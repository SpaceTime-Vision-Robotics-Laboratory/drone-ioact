# Drone Controller

Install `requirements-base.txt` for the common requirements without any 3rd party dependencies, lile `olympe` (from parrot).
See [examples](examples/) for how to run it.

Architecture:

<img alt="arch" src="./arch.png" width="50%">

Every `main` script will contain the following logic:

```python
def main():
    """main fn"""
    drone = SOME_DRONE(ip := drone_ip)
    drone.connect() # establish connection to the drone before any callbacks
    actions_queue = PriorityQueue(maxsize=QUEUE_MAX_SIZE) # how many actions can there be at most in the internal queue

    # data producer thread (1) (drone I/O in -> data/RGB out)
    data_reader = XXXDataReader(drone=drone, ...args...) # XXX = specific drone like Olympe (parrot)
    # data consumer threads (data/RGB in -> I/O out)
    screen_displayer = ScreenDisplayer(drone_in=data_reader) # example of data consumer (show rgb to screen)
    # data consumer & actions producer threads (data/RGB in -> action out)
    kb_controller = KeyboardController(drone_in=data_reader, actions_queue=actions_queue) # keyboard in -> action out
    # actions consumer thread (1) (action in -> drone I/O out)
    actions_mkaer = XXXActionsMaker(drone=drone, actions_queue=actions_queue) # action in -> actual drone action

    while True:
        threads = {
            "Data reader": data_reader.is_alive(),
            "Screen displayer": screen_displayer.is_alive(),
            "Keyboard controller": kb_controller.is_alive(),
            "Olympe actions maker": actions_mkaer.is_alive(),
        }
        if any(v is False for v in threads.values()): # if any thread crashes, stop the application
            logger.info("\n".join(f"- {k}: {v}" for k, v in threads.items()))
            break
    drone.disconnect() # disconnect from the drone.

if __name__ == "__main__":
    main()
```
