#!/bin/bash

export DISPLAY=:0
pgrep 'FrameGeo'
if [ $? != 0 ]
then
python $HOME/Raspberry-Photo-Frame/FrameGeo.py --config-file $HOME/.photo-frame --geouser madvic --dir-check 3600 --waittime 20 --weather-time 300 --logfile /mnt/frododata/temp/Framegeo.log /mnt/frodomedia/photo/Fotos

fi

