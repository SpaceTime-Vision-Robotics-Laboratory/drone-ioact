# Simple keyboard controller and window display with OpenCV

Tested only with the [sphinx-parrot](https://developer.parrot.com/docs/sphinx/installation.html) simulator on Ubuntu 22.04:

After installing:
```bash
# In one terminal: parrot-sphinx drone simulator
wget https://firmware.parrot.com/Versions/anafi2/pc/%23latest/images/anafi2-pc.ext2.zip -P /home/USER/anafi2-pc.ext2.zip
sphinx "/opt/parrot-sphinx/usr/share/sphinx/drones/anafi_ai.drone"::firmware="/home/USER/anafi2-pc.ext2.zip"

# In another terminal: UE4 environment
parrot-ue4-empty # or other

# In a third terminal: this code. The IP may depend on the internal network the sphinx simulator creates.
DRONE_IP=10.202.0.1 python main.py
```
