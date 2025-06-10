#!/bin/bash

#set -eux

SCRIPTS_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

. "$SCRIPTS_DIR"/../.venv/bin/activate

cd "$SCRIPTS_DIR"/.. || exit

trap 'ctrl_c' INT
trap '' USR2

export PYTORCH_ENABLE_MPS_FALLBACK=1

# https://github.com/apache/arrow/issues/36301
export ACERO_ALIGNMENT_HANDLING=ignore

TWICE=0
function ctrl_c() {
    if [ $TWICE -eq 1 ]
    then
    echo "** Trapped second CTRL-C, hard shutdown"
      kill -9 "$SETSID_PID"
      echo "$SETSID_PID"
      pkill -f "CoreMLPlayer/.venv/bin/python -c from multiprocessing.spawn"
      exit 1
    fi
    TWICE=1
    echo "** Trapped CTRL-C" "$SETSID_PID"
    kill -USR2 "$SETSID_PID"
    wait "$SETSID_PID"
    exit 0
}

while true
do
    setsid -w python -m app "$@" | grep -v "🚀" &
    SETSID_PID=$!
    wait $SETSID_PID
    echo RESTARTING
done