#!/bin/bash

export DISPLAY=:0
pgrep 'FrameGeo'
if [ $? != 0 ]
then
~/mypy/bin/python3 $HOME/Raspberry-Photo-Frame/FrameGeo.py --config-file $HOME/.photo-frame --geouser madvic --dir-check 360000 --waittime 20 --weather-time 300 --logfile /mnt/frododata/temp/Framegeo.log /mnt/frodomedia/photo/Fotos

fi

