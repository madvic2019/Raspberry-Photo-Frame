#--coding: utf-8 --
#!/usr/bin/python
import platform
import os
from PIL import Image, ExifTags, ImageFilter # these are needed for getting exif data from images
from PIL.ExifTags import GPSTAGS,TAGS
#############################################
#    Configuration script for FrameGeo program
#
#
#
# Set Up file search prefix depending on platform

if platform.system() == "Windows" :
   PI3DDEMO = os.environ['HOMEPATH']+'/pi3d_demos-master/'
else : #assume it is Raspberry Pi. This can be extended with other platforms
   PI3DDEMO = '/home/pi/pi3d_demos/'
print (PI3DDEMO)


# Default values
GEONAMESUSER = ''
DEFAULT_CONFIG_FILE = './.photo-frame' 
PIC_DIR = './examples' #change this to your images default location folder
CHECK_DIR_TM = 3600.0 # Time to check for directory changes
NUMBEROFROUNDS = 0 # number of rounds before re-fetching images 0 means after one pass

FPS = 20
FIT = True
EDGE_ALPHA = 0.5 # see background colour at edge. 1.0 would show reflection of image
BACKGROUND = (0.2, 0.2, 0.2, 1.0)
RESHUFFLE_NUM = 5 # times through before reshuffling
FONT_FILE = PI3DDEMO + '/fonts/NotoSans-Regular.ttf'

# Use your Locale for these:
CODEPOINTS = '1234567890ABCDEFGHIJKLMNÑOPQRSTUVWXYZ., _-/ÁÉÍÓÚabcdefghijklmnñopqrstuvwxyzáéíóú' # limit to 49 ie 7x7 grid_size
MES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]



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