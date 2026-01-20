#!/usr/bin/bash
# set -ex
export CWD=$(dirname $(readlink -f ${BASH_SOURCE[0]}))
export PROJ_ROOT=$CWD/../../../

ROBOBASE_LOGLEVEL=2 ROBOIMPL_LOGLEVEL=2 python $PROJ_ROOT/examples/maze/main.py random
