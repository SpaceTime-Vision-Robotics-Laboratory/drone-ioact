# Video player on a random video + various neural networks DataProducers

## Usage

```bash
python main.py video.mp4 [--phg_weight_path model_phg.ckpt] [--yolo_weight_path model_yolo.ckpt] [--vre_config_path vre_cfg.yaml]
```

## Supported neural networks
- [PHG-MAE-Distil](../../../roboimpl/data_producers/semantic_segmentation/phg_mae_semantic/phg_mae_semantic_data_producer.py)
    - 150k: [link](https://gitlab.com/video-representations-extractor/video-representations-extractor/-/raw/master/vre_repository/semantic_segmentation/safeuav/weights/model_150k.ckpt?ref_type=heads)
    - 430k: [link](https://gitlab.com/video-representations-extractor/video-representations-extractor/-/raw/master/vre_repository/semantic_segmentation/safeuav/weights/model_430k.ckpt?ref_type=heads)
    - 1M: [link](https://gitlab.com/video-representations-extractor/video-representations-extractor/-/raw/master/vre_repository/semantic_segmentation/safeuav/weights/model_1M.ckpt?ref_type=heads)
    - 4M: [link](https://gitlab.com/video-representations-extractor/video-representations-extractor/-/raw/master/vre_repository/semantic_segmentation/safeuav/weights/model_4M.ckpt?ref_type=heads)
- [YOLO](../../../roboimpl/data_producers/object_detection/yolo/yolo_data_producer.py)
    - Any `.pt` file like `yolo11n.pt` (i.e. from [here](https://huggingface.co/Ultralytics/YOLO11/tree/main)) or even [FastSAM-s.pt](https://github.com/ultralytics/assets/releases/download/v8.4.0/FastSAM-s.pt).
- [VRE Repository](../../../roboimpl/data_producers/vre/vre_data_producers.py)
    - Any representation from [VRE Repository](https://gitlab.com/video-representations-extractor/video-representations-extractor/-/blob/master/vre_repository/__init__.py). If you `pip install video-representations-extractor` it should auto-download any weights file from the repository.

## Controls:
- `ESC` - closes the window
- `SPACE` - pauses or plays the video
- `->` - skips on second ahead
- `<-` - goes one second behind
- `.` - skips one frame ahead
- `,` - skips on frame behind

## Webcam example via ffmpeg + robobase:

```bash
ffmpeg -i https://w3.webcamromania.ro/busteni/index.m3u8 -f rawvideo -pix_fmt rgb24 - | CUDA_VISIBLE_DEVICES=0 VRE_VIDEO_LOGLEVEL=2 ROBOBASE_LOGLEVEL=2 ROBOIMPL_LOGLEVEL=2 ./main.py - --yolo_weights_path yolo11s.pt --yolo_threshold 0.1 --frame_resolution 800 1280 --fps 30
```
