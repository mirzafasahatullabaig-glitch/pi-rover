#!/usr/bin/env bash
# Download the MobileNet-SSD model (person detection). Run from the repo root on the Pi.
set -e
mkdir -p models
wget -q -O models/deploy.prototxt \
  https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/master/deploy.prototxt
wget -q -O models/mobilenet_iter_73000.caffemodel \
  https://github.com/chuanqi305/MobileNet-SSD/raw/master/mobilenet_iter_73000.caffemodel
echo "model downloaded:"
ls -l models/
