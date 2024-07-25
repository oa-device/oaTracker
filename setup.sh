#!/bin/bash

# Determine the shell and run the corresponding setup script
case "$SHELL" in
*/fish)
    fish init-scripts/fish_setup.fish
    ;;
*)
    bash init-scripts/bash_setup.sh
    ;;
esac
