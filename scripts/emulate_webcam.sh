#!/bin/bash

#set -eux

SCRIPTS_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT

NAME_A=forward
USB_NAME_A="USB Camera2"
DEVICE_NUMBER_A=0

sudo modprobe -r v4l2loopback
sudo modprobe v4l2loopback devices=1 video_nr=$DEVICE_NUMBER_A max_buffers=4 exclusive_caps=1 card_label="$USB_NAME_A"

ffmpeg -nostats -loglevel 0 -stream_loop -1 -re -i /home/deagle/Downloads/012.mp4 -f v4l2 -vcodec rawvideo -s 1920x1080 /dev/video$DEVICE_NUMBER_A &

echo "Fake webcam started"
echo " - /dev/video$DEVICE_NUMBER_A: $USB_NAME_A ($NAME_A)"

sleep infinity
