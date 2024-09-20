#!/bin/bash

#set -eux

SCRIPTS_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

cd $SCRIPTS_DIR/..

if ! command -v virtualenv &> /dev/null
then
    echo "virtualenv could not be found"
    exit
fi

virtualenv .venv

. ./venv/bin/activate

pip install -r requirements.txt
