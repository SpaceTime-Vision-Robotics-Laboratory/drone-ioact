#!/usr/bin/bash
# set -ex
export CWD=$(dirname $(readlink -f ${BASH_SOURCE[0]}))

echo "================= Video UDP Screenshot ================="
bash $CWD/video-udp-screenshot/run.sh
echo "========================= Maze ========================="
bash $CWD/maze/run.sh
