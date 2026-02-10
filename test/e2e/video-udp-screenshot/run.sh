#!/usr/bin/bash
# set -ex
export CWD=$(dirname $(readlink -f ${BASH_SOURCE[0]}))
export PROJ_ROOT=$CWD/../../../
PORT=9999

export ROBOBASE_LOGLEVEL=2
export ROBOIMPL_LOGLEVEL=2

function wait_for_start {
    n_tries=$1
    port=$2
    i=0
    while (( i < n_tries )); do
        res=$(lsof -i udp:$port -t)
        if [ "$?" == "0" ]; then
            echo "found pid after $i tries"
            return 0
        fi
        i=$((i+1))
        sleep 0.1
    done
    kill $$
}

echo "-- starting end to end test"

echo "-- cleanup"
( kill $(lsof -i udp:$PORT -t) 2>/dev/null ) || echo "no server to kill"
rm -f frame.png # uses "cwd" of the user

$CWD/main.py $CWD/test_video.mp4 --port $PORT &
PID_MAIN=$!
wait_for_start 100 $PORT

res=$(echo "RANDOM" | nc -w1 -u 127.0.0.1 $PORT)
expected="Unknown message: RANDOM"
test "$res" == "$expected" || ( echo -e "Expected $expected.\nGot $res."; kill $PID_MAIN $$; )

res=$(echo "GO_FORWARD 1" | nc -w1 -u 127.0.0.1 $PORT)
expected="OK"
test "$res" == "$expected" || ( echo -e "Expected $expected.\nGot $res."; kill $PID_MAIN $$; )

res=$(echo "TAKE_SCREENSHOT" | nc -w1 -u 127.0.0.1 $PORT)
expected="OK"
test "$res" == "$expected" || ( echo -e "Expected $expected.\nGot $res."; kill $PID_MAIN $$; )

[[ -f frame.png && $(head -c 4 frame.png) == $'\x89PNG' ]] \
  && echo "OK: Valid PNG" || ( echo "Invalid or missing PNG"; kill $PID_MAIN $$; rm -f frame.png )

kill $PID_MAIN
rm -f frame.png
