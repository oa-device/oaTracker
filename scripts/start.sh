#!/bin/bash

#set -eux

SCRIPTS_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

. $SCRIPTS_DIR/../.venv/bin/activate

cd $SCRIPTS_DIR/..

while true
do
    python -m app
    echo 1
    pkill -KILL -f './scripts/start.sh'; pkill -KILL -f 'python -m app'; pkill -KILL -f '.venv/bin/python'
done
