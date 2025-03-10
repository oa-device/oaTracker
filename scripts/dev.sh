#!/bin/bash

#set -eux

SCRIPTS_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

cd $SCRIPTS_DIR/..

if ! command -v virtualenv &> /dev/null
then
    echo "virtualenv could not be found"
    exit
fi

. ./venv/bin/activate

sudo echo 'Sudo active'

./scripts/emulate_two_webcams.sh &
./scripts/open_docs.sh &
./scripts/start.sh

