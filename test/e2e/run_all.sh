#!/usr/bin/bash
# set -ex
export CWD=$(dirname $(readlink -f ${BASH_SOURCE[0]}))

bash $CWD/video-udp-screenshot/run.sh
bash $CWD/maze/run.sh
