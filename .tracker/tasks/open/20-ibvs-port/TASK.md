# IBVS Port to Robobase — Implementation Plan

Port of the IBVS pipeline from [nser-ibvs-drone](https://github.com/SpaceTime-Vision-Robotics-Laboratory/nser-ibvs-drone) as a standalone application on top of robobase/roboimpl.

**Rule**: Keep only remaining steps. Remove completed work from this plan — the code and docs.md are the record.

## Target file layout

```
roboimpl/envs/olympe_parrot/
  olympe_env.py                              # done: get_state() with flying_state + gimbal
  olympe_actions.py                          # done: unified (velocity, duration) actions + PILOTING
  docs.md                                    # done: Olympe SDK reference, ARSDK internals, layer cake

examples/olympe/2-nser-ibvs/
  main.py                                    # done: ibvs_olympe_actions_fn + INITIALIZE_FLIGHT + detection pipeline
  main_video.py                              # done: video replay with detection pipeline (AutofollowReplayEnv TODO)
  auto_follow_logs_frame_reader.py           # done: frame reader for autofollow logs
  detection/                                 # done: YOLO + MaskSplitter pipeline
    __init__.py                              # package init
    mask_splitter_data_producer.py            # DataProducer: front/back mask splitting via neural net
    mask_splitter_nn.py                      # MaskSplitterNet: U-Net that splits segmentation into front/back
  ibvs/                                      # new module: IBVS control law
    __init__.py                              # package init
    math.py                                  # ImageBasedVisualServo + velocity_to_command()
    controller.py                            # IBVSControllerFn: data dict -> Action | None
```

---

## Step 1: Port IBVS math + velocity-to-command

**Why**: This is the core control law — the entire reason the project exists. It takes image feature errors (where the target is vs. where it should be, in pixels) and computes camera velocities via the interaction matrix and pseudoinverse. Without this, there is no visual servoing. It's a clean port from nser-ibvs-drone: the math is proven to work on the real drone, we're just extracting it from the tightly-coupled original into a standalone module with no framework dependencies.

**File**: `examples/olympe/2-nser-ibvs/ibvs/math.py` (new file)

Port from three source files in nser-ibvs-drone:
- [ibvs_controller.py:6-135](https://github.com/SpaceTime-Vision-Robotics-Laboratory/nser-ibvs-drone/blob/main/nser_ibvs_drone/ibvs/ibvs_controller.py#L6-L135) — `ImageBasedVisualServo` class
- [ibvs_math_fcn.py:7-19](https://github.com/SpaceTime-Vision-Robotics-Laboratory/nser-ibvs-drone/blob/main/nser_ibvs_drone/ibvs/ibvs_math_fcn.py#L7-L19) — `e2h()` helper
- [target_tracker.py:127-172](https://github.com/SpaceTime-Vision-Robotics-Laboratory/nser-ibvs-drone/blob/main/nser_ibvs_drone/detection/target_tracker.py#L127-L172) — `calculate_movement()`

**Important**: the IBVS splitter pipeline does NOT use PID. The PID configs in nser-ibvs-drone (`pid_x.yaml`, `pid_forward.yaml`) are for a different control mode (simple tracker). This is pure proportional control with adaptive gain.

#### `ImageBasedVisualServo` class (~110 LOC)

```python
class ImageBasedVisualServo:
    """IBVS control law: computes camera velocities from image feature errors."""
    def __init__(self, camera_intrinsic: np.ndarray, goal_points: list[tuple[int, int]],
                 lambda_factor: float = 0.30, estimated_depth: float = 1.0) -> None:
        self.K = camera_intrinsic                    # 3x3 intrinsic matrix
        self.Kinv = np.linalg.inv(self.K)
        self.lambda_factor = np.diag([lambda_factor * 2.5, lambda_factor * 2.5, lambda_factor * 1.15])
        self.lambda_factor_low = np.diag([0.5, 0.5, 0.1])
        self.goal_points_flatten = np.hstack(goal_points)
        self.Z = estimated_depth
        self.err_threshold = 60                      # pixels — switches gain regime
        self.err_uv_values: list[float] = []

    def set_current_points(self, points: list[tuple[int, int]]) -> None: ...
    def compute_interaction_matrix(self) -> np.ndarray: ...
    def compute_depths(self, pixels: np.ndarray) -> np.ndarray: ...
    def compute_velocities(self) -> tuple[np.ndarray, dict]: ...
```

Key math:
- Builds 2N x 3 interaction matrix (reduced: only roll/pitch/yaw, no translation)
- Per-point row: `K[:2,:2] @ [[-1/Z, 0, y], [0, -1/Z, -x]]`
- Depth estimation: `Z_i = Z * sqrt(x_n^2 + y_n^2 + 1)` (see note below)
- Adaptive gain: `lambda_factor` switches from `[0.75, 0.75, 0.345]` to `[0.5, 0.5, 0.1]` when error norm < 60 pixels
- `vel = lambda @ pinv(J) @ error_uv`

**Depth estimation**: The interaction matrix requires per-point depth, but there is no depth sensor. `estimated_depth` (default `1.0` m) is a fixed constant set at construction time and never updated during flight — the original nser-ibvs-drone never overrides this default. Per-point depths are derived geometrically: `Z_i = Z * sqrt(x_n^2 + y_n^2 + 1)` where `x_n, y_n` are normalized image coordinates (`K_inv @ pixel`). This is a flat-image-plane-to-sphere correction: the image sensor is flat but the target sits on a sphere centered at the camera, so edge pixels are geometrically farther. In practice it's a mild radial gradient — concentric circles of equal depth around the principal point. For the Anafi camera (~69° HFOV, 640x360), the range is roughly **1.0x at center to ~1.27x at corners** (~27% variation). This is a standard IBVS approximation — the control law is robust to coarse depth estimates (even off by 2-3x) because the pseudoinverse + feedback loop naturally compensates. If the drone oscillates or converges too slowly, the first thing to try is estimating `Z` from the known physical size of the target vs. its apparent pixel size — but nser-ibvs-drone never needed that.

**Hardcoded parameters in the original**: The original nser-ibvs-drone stores camera intrinsics and goal points in external files, NOT inline. The `ImageBasedVisualServo` constructor takes `(K, goal_points)` and uses defaults for the rest:
- **Camera intrinsics** — loaded from pickle files via `infer_intrinsic_matrix(camera_params_path)`. The sim Anafi 4K values (from `assets/camera_parameters/sim-anafi-4k/cam.txt`): `fx = fy = 931.206`, `cx = 640`, `cy = 360` (for 1280x720). Separate param sets exist for sim-anafi-4k, sim-anafi-ai, and real-full-res. The code can scale the matrix for different resolutions.
- **Goal points** — loaded from JSON files (`GOAL_FRAME_POINTS_PATH_45`, `_45_SIM`, `_45_REAL`, `_90` for different gimbal angles). The code reads `json["bbox_oriented_points"][:4]` — the 4 oriented bounding box corners at the desired target position in the image.
- **`estimated_depth`** — defaults to `1.0`, never overridden at the call site.
- **`lambda_factor`** — defaults to `0.30`, never overridden at the call site.

For the robobase port, we can start by hardcoding the sim Anafi 4K intrinsics and a default goal point set, and expose them as CLI args for configurability.

#### `velocity_to_command()` function (~40 LOC)

```python
def velocity_to_command(velocities: np.ndarray,
                        max_linear_speed: float = 2.0,
                        max_angular_speed_deg: float = 60.0,
                        yaw_dead_zone: float = 8.0) -> tuple[int, int, int, int]:
    """Convert IBVS velocities [roll, pitch, yaw] to piloting percentages.
    Returns: (x_cmd, y_cmd, z_cmd=0, rot_cmd) as ints in [-100, 100]."""
    ...
```

Conversion rules:
- `roll = ceil(100 * vel[0] / max_linear_speed)` (max_linear_speed = 2 m/s)
- `pitch = ceil(-100 * vel[1] / max_linear_speed)`
- `yaw = 100 * vel[2] / max_angular_speed` (max_angular_speed = 60 deg/s)
- Yaw dead zone: if `|yaw| < 8`, set yaw = 0
- Velocity dead zone: if `0.002 <= |vel| <= 0.005`, clamp to +/-1

Pure numpy, no PID, no framework dependency. Also create `ibvs/__init__.py` (empty).

**~150 lines total.**

## Step 2: Write the IBVSControllerFn

**Why**: This is the glue between perception and actuation — the "decision" in the perception-decision-action loop. In nser-ibvs-drone, this logic was buried inside a 200-line `_process_frame()` that also handled threading, YOLO calls, display updates, and drone commands. By expressing it as a pure `ControllerFn` (data dict in, Action out), robobase handles all the threading and scheduling automatically. The controller becomes ~30 lines of stateless decision logic — easy to test, easy to swap, and decoupled from both the perception pipeline (runs in DataProducer threads) and actuation (runs in Actions2Environment thread).

**File**: `examples/olympe/2-nser-ibvs/ibvs/controller.py` (new file)

Refs: [ibvs_splitter_processor.py:43-102](https://github.com/SpaceTime-Vision-Robotics-Laboratory/nser-ibvs-drone/blob/main/nser_ibvs_drone/processors/ibvs_splitter_processor.py#L43-L102) (original `_process_frame()` — our ControllerFn extracts only the IBVS decision), [target_tracker.py:140-142](https://github.com/SpaceTime-Vision-Robotics-Laboratory/nser-ibvs-drone/blob/main/nser_ibvs_drone/detection/target_tracker.py#L140-L142) (`set_current_points()` -> `compute_velocities()` -> command — the 3-line core we preserve).

```python
class IBVSControllerFn:
    """ControllerFn for IBVS: data dict -> Action | None.
    Passed to robot.add_controller(), which wraps it in a Controller thread.
    """
    def __init__(self, goal_points: list[tuple[int, int]], camera_intrinsics: np.ndarray,
                 lambda_factor: float = 0.30, estimated_depth: float = 1.0) -> None:
        self.ibvs = ImageBasedVisualServo(
            camera_intrinsic=camera_intrinsics,
            goal_points=goal_points,
            lambda_factor=lambda_factor,
            estimated_depth=estimated_depth,
        )

    def __call__(self, data: dict[str, DataItem]) -> Action | None:
        if data["bbox_oriented"] is None:
            return None  # no target detected

        self.ibvs.set_current_points(data["bbox_oriented"])
        velocities, _logs = self.ibvs.compute_velocities()
        x_cmd, y_cmd, z_cmd, rot_cmd = velocity_to_command(velocities)
        return Action("PILOTING", (x_cmd, y_cmd, rot_cmd, z_cmd, 0.15))
```

**Note on action name**: Uses `"PILOTING"` (already in `OLYMPE_SUPPORTED_ACTIONS`) instead of a custom `"PILOT"` action. The `PILOTING` action in `olympe_actions_fn` takes `(roll, pitch, yaw, gaz, piloting_time)` — the IBVSControllerFn must match this parameter order.

**~30 lines.**

## Step 3: Wire the IBVS controller into main.py and main_video.py

**Why**: Both entrypoints already have the full perception pipeline working (YOLO + MaskSplitter + ScreenDisplayer). Adding the IBVS controller as a second controller on the same DataChannel completes the port. Two controllers run concurrently: IBVS pushes PILOTING actions for autonomous tracking, while ScreenDisplayer provides live visualization and keyboard override (the human can LAND at any time). This dual-controller pattern is exactly what robobase was designed for and what was painful to build manually in nser-ibvs-drone.

**Files**: `examples/olympe/2-nser-ibvs/main.py` and `main_video.py` (both existing)

Refs: [ibvs_splitter_controller.py:12-72](https://github.com/SpaceTime-Vision-Robotics-Laboratory/nser-ibvs-drone/blob/main/nser_ibvs_drone/controllers/ibvs_splitter_controller.py#L12-L72) (original wiring — our `main.py` replaces this entire file).

#### main.py changes

1. Add import: `from ibvs.controller import IBVSControllerFn`
2. Pre-queue: `actions_queue.put(Action("INITIALIZE_FLIGHT"))` before `robot.run()`
3. Add the IBVS controller before `robot.run()`:
```python
ibvs_fn = IBVSControllerFn(
    goal_points=args.goal_points,
    camera_intrinsics=args.camera_intrinsics,
)
robot.add_controller(ibvs_fn, name="IBVS")
```
4. Add CLI args for `--goal_points` and `--camera_intrinsics` (or hardcode defaults for the Anafi camera)

After this, both controllers push to the same ActionsQueue. Keyboard actions (LAND, DISCONNECT) go through alongside IBVS PILOTING commands. `INITIALIZE_FLIGHT` executes first (pre-queued), then the control loop takes over.

#### main_video.py changes

**TODO: Replace VideoPlayerEnv + AutoFollowLogsFrameReader with AutofollowReplayEnv.** The current `main_video.py` uses `VideoPlayerEnv` with an `AutoFollowLogsFrameReader` hack to read frames from autofollow logs. This should be replaced with a dedicated `AutofollowReplayEnv` — a new environment that natively loads the full autofollow log directory and exposes everything autofollow recorded during the flight as data modalities (not just RGB frames, but also the actions autofollow took, flight state, gimbal angles, GPS, etc.). This gives the IBVS controller access to ground-truth autofollow behavior for comparison/evaluation, and eliminates the frame-reader overwrite workaround. The new env would replay the flight log as its own environment rather than pretending to be a video player.

Beyond the env replacement, the same IBVS wiring applies: add the IBVSControllerFn as a second controller, but without `INITIALIZE_FLIGHT` (replay env, not a live drone). The IBVS controller produces PILOTING actions that can be compared against the original autofollow actions from the logs to evaluate the control law before flying.

**~20 lines changed per file.**

---

## Timing considerations

### Command queuing vs dropping

In nser-ibvs-drone, excess IBVS commands are silently dropped (semaphore). In robobase, they queue in ActionsQueue. The current `main.py` uses `Queue(maxsize=30)` — this could cause command lag. Fix: use `Queue(maxsize=1)` so stale commands are superseded, or add `freq_barrier()` in IBVSControllerFn.

### Frame-skipping

The original halves the control rate (`count % 2`). In robobase, the effective rate is naturally limited by producer pipeline latency (YOLO + MaskSplitter is the bottleneck). If the controller runs too fast, add `freq_barrier()` or throttle the producer worker.

### Gain transfer

The IBVS control law (`vel = lambda @ pinv(J) @ err`) is proportional-only with no time dependence. Gains map pixel error to velocity directly — no dt sensitivity unlike PID. The lambda gains should transfer directly from nser-ibvs-drone. The main risk is command queuing (above), not gain mismatch.

---

## Summary

| Step | File(s) | ~LOC | What |
|------|---------|------|------|
| 1 | `examples/olympe/2-nser-ibvs/ibvs/math.py` (new) | 150 | IBVS control law + velocity-to-command |
| 2 | `examples/olympe/2-nser-ibvs/ibvs/controller.py` (new) | 30 | IBVSControllerFn callable |
| 3 | `examples/olympe/2-nser-ibvs/main.py` + `main_video.py` | 40 | Wire IBVS controller into both entrypoints |
| **Remaining** | | **~220** | **all example code, no roboimpl changes** |
