#--coding: utf-8 --
#!/usr/bin/python3
from __future__ import absolute_import, division, print_function, unicode_literals
''' Simplified slideshow system using ImageSprite and without threading for background
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
python3 FrameGeo [Image Path] [--config-file configfilename] [--waittime delaybetweenslides] [--shuffle True|False] [--geonamesuser username]

Support of geo tagging in EXIF to show location of photo in slide show (using GeoNames service)
Persistent images list: enables restart with same images list and resume from last shown image.
Optimized file list creation to enable (very) large images catalog.
Use logging Module instead of print


Copyright (c) Victor Diaz  2020
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), 
to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, 
distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. 
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, 
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
import os
import shutil
import time 
import random
import pi3d
import argparse
import stat
import json
import math
import subprocess



from PIL import Image, ExifTags, ImageFilter # these are needed for getting exif data from images
from PIL.ExifTags import GPSTAGS,TAGS
import exif # Direct access to EXIF tags
from geopy.geocoders import GeoNames,Nominatim

import FrameConfig as config


#############################
SHOW_LOCATION = True

#####################################################
BLUR_EDGES = True # use blurred version of image to fill edges - will override FIT = False
BLUR_AMOUNT = 12 # larger values than 12 will increase processing load quite a bit
BLUR_ZOOM = 1.0 # must be >= 1.0 which expands the backgorund to just fill the space around the image
KENBURNS = False # will set FIT->False and BLUR_EDGES->False
KEYBOARD = True  # set to False when running headless to avoid curses error. True for debugging
#####################################################
# these variables can be altered using MQTT messaging
#####################################################
TIME_DELAY = 15 # default timer between slides
fade_time = 0.5
quit = False
paused = False # NB must be set to True after the first iteration of the show!
FPS = 20
FIT = True
EDGE_ALPHA = 0.5 # see background colour at edge. 1.0 would show reflection of image
BACKGROUND = (0.2, 0.2, 0.2, 1.0)
RESHUFFLE_NUM = 5 # times through before reshuffling


def get_files(dir,config_file,shuffle): # Get image files names to show
  
  global last_file_change
  file_list = None
  extensions = ['.png','.jpg','.jpeg','.bmp'] # can add to these
  if os.path.exists(config_file) : # If there is a previous file list stored, just use it
    print("Config file exists, open for reading",config_file)
    with open(config_file, 'r') as f:
        try:
          file_list=json.load(f)
          if len(file_list)>0:
            if len(os.path.commonprefix((file_list[0],dir))) < len(dir) :
              print("Directory is different from config file ",os.path.dirname(file_list[0]), " -- ",dir," reloading")
              file_list=None
          else:
            file_list=None
        except:
          print(config_file , 'Config File is not correct')   
            
  if file_list is None :
    print("Config File is not existing or corrupt")
    print("Clean config file for numbers")
    if os.path.exists(config_file+".num"):
      os.remove(config_file+".num")
    file_list=[]
    for root, _dirnames, filenames in os.walk(dir):
      mod_tm = os.stat(root).st_mtime # time of alteration in a directory
      if mod_tm > last_file_change:
        last_file_change = mod_tm
      for filename in filenames:
        ext = os.path.splitext(filename)[1].lower()
        if ext in extensions and not '.AppleDouble' in root and not filename.startswith('.'):
          file_path_name = os.path.join(root, filename)
          file_list.append(file_path_name) 
        if (len(file_list) % 1000 == 0) : # print every 1000 files detected
          print(len(file_list)) 
    if shuffle:
      random.shuffle(file_list)
    else:
      file_list.sort() # if not shuffled; sort by name
    
    with open(config_file,'w') as f: #Store list in config file
      json.dump(file_list, f, sort_keys=True)
      print("List written to ",config_file) 

  print(len(file_list)," image files found")
  return file_list, len(file_list) # tuple of file list, number of pictures
  

