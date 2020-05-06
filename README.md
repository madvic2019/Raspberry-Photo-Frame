# Photo Frame for the Raspberry Pi

I took the PictureFrame program from pi3d demos (https://github.com/pi3d/pi3d_demos) and added geo tagging support. 

The images are shown with text information: Location and Date of capture, if available.

GPS coordinates are extracted from EXIF metadata, then converted to location name using online service GeoNames (using geopy wrapper)
You need to set up an account (free) in www.geonames.org



 
Optimized file list creation to enable (very) large images catalog. On creation of ifle list, only file name is checked, 

Persistent images list: enables restart with same images list and resume from last shown image.
    The program stores the list of files to be shown in {configfilename} and the last index used in  {configfilename}.num
    This way when program is stopped (or Raspberry rebooted, crashed, etc), it will retain the last status for next run, speeding up start up. This is helpful for very large number of images.

usage: FrameGeo.py [-h] [--config-file CONFIG] [--waittime WAITTIME]
                   [--shuffle SHUFFLE] [--geouser GEOUSER]
                   [--dir-check DIRCHECKTM]
                   [ImagePath]


optional arguments:
  -h, --help            show this help message and exit
  --config-file CONFIG  Configuration file holding list of image files
  --waittime WAITTIME   Amount of time to wait before showing the next image.
  --shuffle SHUFFLE     Shuffle pictures list
  --geouser GEOUSER     User Name for GeoNames server
  --dir-check DIRCHECKTM
                        Interval between check directories

