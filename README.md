# MarcoFotos
This is a Picture Frame project for the Raspberry pi, based on pi3d libraries and demos.

Simplified slideshow system using ImageSprite and without threading for background
loading of images (so may show delay for v large images).
    
Also has a minimal use of PointText and TextBlock system with reduced  codepoints
and reduced grid_size to give better resolution for large characters.
    

USING exif info to rotate images

    by default the global KEYBOARD is set False so the only way to stop the
    probram is Alt-F4 or reboot. If you intend to test from command line set
    KEYBOARD True. After that:
    ESC to quit, 's' to reverse, any other key to move on one.
    
ADDED by V. Diaz:

Commandline arguments defined:
python3 FrameGeo [--help] [Image Path] [--config-file configfilename] [--waittime delaybetweenslides] [--shuffle True|False] [--geonamesuser username]

Support of geo tagging in EXIF to show location of photo in slide show (using GeoNames service)
Optimized file list creation to enable (very) large images catalog. On creation of ifle list, only file name is checked, 

Persistent images list: enables restart with same images list and resume from last shown image.
    The program stores the list of files to be shown in {configfilename} and the last index used in  {configfilename}.num
    This way when program is stopped (or Raspberry rebooted, crashed, etc), it will retain the last status for next run, speeding up start up. This is helpful for very large number of images.

