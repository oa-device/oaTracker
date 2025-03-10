#!/bin/bash

#set -eux

SCRIPTS_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT

NAME_A=forward
NAME_B=reverse
USB_NAME_A="USB Camera2"
USB_NAME_B="USB Camera2"
DEVICE_NUMBER_A=0
DEVICE_NUMBER_B=1

sudo modprobe -r v4l2loopback
sudo modprobe v4l2loopback devices=2 video_nr=$DEVICE_NUMBER_A,$DEVICE_NUMBER_B max_buffers=4 exclusive_caps=1 card_label="$USB_NAME_A","$USB_NAME_B"

ffmpeg -nostats -loglevel 0 -stream_loop -1 -re -i $SCRIPTS_DIR/video-$NAME_A-10.mp4 -f v4l2 -vcodec rawvideo -s 1280x720 /dev/video$DEVICE_NUMBER_A &
ffmpeg -nostats -loglevel 0 -stream_loop -1 -re -i $SCRIPTS_DIR/video-$NAME_B-10.mp4 -f v4l2 -vcodec rawvideo -s 1280x720 /dev/video$DEVICE_NUMBER_B &

echo "Fake webcams started"
echo " - /dev/video$DEVICE_NUMBER_A: $USB_NAME_A ($NAME_A)"
echo " - /dev/video$DEVICE_NUMBER_B: $USB_NAME_B ($NAME_B)"

sleep infinity
