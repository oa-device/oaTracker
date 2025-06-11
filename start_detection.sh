#!/usr/bin/env bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

cd "$DIR" || exit

./scripts/start.sh | awk '{print strftime("%Y-%m-%d %H:%M:%S"), $0}' &>> output.txt
