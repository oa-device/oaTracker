#!/bin/bash

#set -eux

SCRIPTS_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

. $SCRIPTS_DIR/../.venv/bin/activate

cd $SCRIPTS_DIR/..

while true
do
    python -m app
    killall -9 python &> /dev/null
    killall -9 Python &> /dev/null
done
