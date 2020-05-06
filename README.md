# Photo Frame for the Raspberry Pi

I took the PictureFrame program from pi3d demos (https://github.com/pi3d/pi3d_demos) and added geo tagging support. 

The images are shown with text information: Location and Date of capture, if available.

GPS coordinates are extracted from EXIF metadata, then converted to location name using online service GeoNames (using https://github.com/geopy/geopy)

You need to set up an account (free) in www.geonames.org
 
I also optimized the file list creation in order to manage large images catalogues. On creation of file list, only file name is checked, postpone costly operations (like EXIF data extraction) to the rendering phase.

The images list is persistent, that enables restart with same images list and resume from last shown image. This is handy if you want to turn off the display and come back where you left (e.g. using crontab). You can even reboot the Raspberry and the Picture Frame resumes where it was before.

The program stores the list of files to be shown in "configfilename" and the last index used in  "configfilename".num

usage: python3 FrameGeo.py [-h] [--config-file CONFIG] [--waittime WAITTIME]
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

