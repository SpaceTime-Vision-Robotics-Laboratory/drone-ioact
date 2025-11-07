# Drone Controller

Install `requirements-base.txt` for the common requirements without any 3rd party dependencies, lile `olympe` (from parrot).
See [examples](examples/) for how to run it.

Architecture:

<img alt="arch" src="./arch.png" width="50%">

Every `main` script will contain the following logic:

```python
def main():
    """main fn"""
    drone = XXXDrone(ip := drone_ip) # XXX = specific real or simulated drone like Olympe
    drone.connect() # establish connection to the drone before any callbacks
    actions_queue = ActionsQueue(maxsize=QUEUE_MAX_SIZE) # defines the list of actions understandable by XXX as well!

    # data producer thread (1) (drone I/O in -> data/RGB out)
    data_reader = XXXDataReader(drone=drone, ...args...) # thread that reads data from the drone and makes it available
    # data consumer threads (data/RGB in -> I/O out)
    screen_displayer = ScreenDisplayer(drone_in=data_reader) # example of data consumer (show rgb to screen)
    # data consumer & actions producer threads (data/RGB in -> action out)
    kb_controller = KeyboardController(drone_in=data_reader, actions_queue=actions_queue) # keyboard in -> action out
    # actions consumer thread (1) (action in -> drone I/O out)
    actions_maker = XXXActionsMaker(drone=drone, actions_queue=actions_queue) # action in -> actual drone action

    threads: dict[str, threading.Thread] = {
        "Screen displayer": screen_displayer,
        "Keyboard controller": kb_controller,
        "Actions maker": actions_maker,
    }
    [v.start() for v in threads.values()] # start the threads

    while True:
        if any(not v.is_alive() for v in threads.values()) or not data_reader.is_streaming():
            logger.info(f"{data_reader} streaming: {data_reader.is_streaming()}")
            logger.info("\n".join(f"- {k}: {v}" for k, v in threads.items()))
            break
        time.sleep(1) # important to not throttle everything with this main thread
    drone.disconnect() # disconnect from the drone.

if __name__ == "__main__":
    main()
```
