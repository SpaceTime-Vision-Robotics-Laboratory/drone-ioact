# Drone Controller

Install `requirements-base.txt` for the common requirements without any 3rd party dependencies, lile `olympe` (from parrot).
See [examples](examples/) for how to run it.

Architecture:

<img alt="arch" src="./arch.png" width="50%">

The two 'core' components of any robotics application are: the *data channel* and the *actions queue*. The data consumers interact with the drone (or any robot) to get raw data and write them to the data channel, while the data consumers interact with the channel and always have access to the latest data. Some data consumers are also action products and write to the actions queue. Then, the actions consumer reads one action at a time from the actions queue and sends raw actions to the drone.

The usual flow is like this:
```

 Drone  -- raw data --> Data Producer --> Data Channel       Actions Queue  <-- Actions Consumer -- raw action --> Drone
(robot)                                  (rgb, pose...)     (LIFT, MOVE...)                                       (robot)
                                               ↓                   ↑
                                        [Data Consumer1 ~ Actions Producer1]
                                        [Data Consumer2 ~         n/a      ]
                                        [Data Consumer3 ~ Actions Producer3]
                                        [Data Consumer4 ~         n/a      ]
```

Every `main` script will contain the following logic:

```python
def main():
    """main fn"""
    drone = XXXDrone(ip := drone_ip) # XXX = specific real or simulated drone like Olympe
    drone.connect() # establish connection to the drone before any callbacks
    actions_queue = ActionsQueue(maxsize=QUEUE_MAX_SIZE, actions=["a1", "a2", ...]) # defines the generic actions
    data_channel = DataChannel(supported_types=["rgb", "pose", ...], eq_fn=lambda a, b: a["rgb"] == b["rgb"]) # defines the data types and how to compare equality (i.e. drone produced same frame twice)

    # defines the threads of this application: all the data & actions producers and consumers.
    data_producer = XXXDataProducer(drone, data_channel) # populates the data channel with RGB & pose from drone
    screen_displayer = ScreenDisplayer(data_channel) # example of data consumer (show rgb to screen)
    kb_controller = KeyboardController(data_channel, actions_queue) # keyboard in -> action out
    actions_maker = XXXActionsConsumer(drone, actions_queue) # converts a generic action to an actual drone action

    threads = ThreadGroup({ # simple dict[str, Thread] wrapper to manage all of them at once.
        "Data producer": data_producer,
        "Screen displayer": screen_displayer,
        "Keyboard controller": kb_controller,
        "Actions maker": actions_maker,
    }).start()

    while not threads.is_any_dead(): # wait for any of them to die or drone to disconnect
        time.sleep(1) # important to not throttle everything with this main thread

    drone.disconnect() # disconnect from the drone.
    threads.join(timeout=1) # stop all the threads

if __name__ == "__main__":
    main()
```
