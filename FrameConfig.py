#--coding: utf-8 --
#!/usr/bin/python
import platform
import os,sys
from PIL import Image, ExifTags, ImageFilter # these are needed for getting exif data from images
from PIL.ExifTags import GPSTAGS,TAGS
#############################################
#    Configuration script for FrameGeo program
#
#
#
# Set Up file search prefix depending on platform, as examples
uname=platform.uname() # tuple with (system, node, release, version, machine, processor)

if uname.system == "Windows" :
   PI3DDEMO = os.environ['HOMEPATH']+'/pi3d_demos-master'
   BUTTONS = False
elif "aarch64" == uname.machine or "armv7l" == uname.machine: 
   PI3DDEMO = '/usr/local/lib/pi3d_demos' # requires copying downloaded demos from https://github.com/pi3d/pi3d_demos/archive/master.zip
   BUTTONS = True
   from gpiozero import Button
else :
   PI3DDEMO = '/home/victor/pi3d_demos' # assume in a Linux environment it will be located directly on user home
   BUTTONS = False
   
print (PI3DDEMO)


# Default values
GEONAMESUSER = ''
DEFAULT_CONFIG_FILE = './.photo-frame'
PIC_DIR = './examples' #change this to your images default location folder
BKUP_DIR = '.backup-MarcoFotos' # This will be used to store modified or deleted image files. Must exist
CHECK_DIR_TM = 3600.0 # Time to check for directory changes
NUMBEROFROUNDS = 1 # number of rounds before re-fetching images 0 means after one pass

FPS = 20
FIT = True
EDGE_ALPHA = 0.5 # see background colour at edge. 1.0 would show reflection of image
BACKGROUND = (0.2, 0.2, 0.2, 1.0)
RESHUFFLE_NUM = 5 # times through before reshuffling
FONT_FILE = PI3DDEMO + '/fonts/NotoSans-Regular.ttf'

# Use your Locale for these:
CODEPOINTS = '1234567890:;ABCDEFGHIJKLMNÑOPQRSTUVWXYZ., _-/ÁÉÍÓÚabcdefghijklmnñopqrstuvwxyzáéíóú' # limit to 49 ie 7x7 grid_size
#CODEPOINTS=list(range(32,255))
MES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
TIME_FORMAT="%d/%m/%Y %H:%M:%S"




#####################################################
# Prepare EXIF data extraction (just instance some constants)
#####################################################
EXIF_DATID = None
EXIF_ORIENTATION = None
EXIF_GPS = None
for k in ExifTags.TAGS:
  if ExifTags.TAGS[k] == 'DateTimeOriginal':
    EXIF_DATID = k
  if ExifTags.TAGS[k] == 'Orientation':
    EXIF_ORIENTATION = k
  if ExifTags.TAGS[k] == 'GPSInfo' :
    EXIF_GPS = k
