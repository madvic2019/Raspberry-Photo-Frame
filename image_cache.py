#--coding: utf-8 --
#!/usr/bin/python3
from __future__ import absolute_import, division, print_function, unicode_literals
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

'''
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
  
'''


# Create a dictionary to store cached file paths
cached_files = {}

def cache_file(file_name,source,local_cache_path):
    if file_name in cached_files:
        print(f"{file_name} is already cached.")
        return

    source_file_path = os.path.join(source, file_name)
    destination_file_path = os.path.join(local_cache_path, file_name)

    try:
        shutil.copy(source_file_path, destination_file_path)
        cached_files[file_name] = destination_file_path
        print(f"{file_name} cached successfully.")
    except FileNotFoundError:
        print(f"File {file_name} not found on the network drive.")
    except Exception as e:
        print(f"An error occurred while caching {file_name}: {e}")


def main(
    startdir,                      # Root folder for images cache in local storage
    config_file,                   # File with list of file names. Comes from FrameGeo, so config_file.num is also present and gives the last file used.
    number_of_files,                # number of files to be cached, starting with last used file from config_file.num
    network_drive_path
    ) :

        
# List of files to be cached locally
    files_to_cache = json.load(open(config_file,'r'))
    first_file_number = json.load(open(config_file+".num",'r'))[1]
    
    for i in range(first_file_number,first_file_number+number_of_files):
        cache_file(files_to_cache[i],network_drive_path,startdir)

    # Now you can access the cached files quickly using the paths stored in the 'cached_files' dictionary
    print("Cached files:")
    for cached_file_name, cached_file_path in cached_files.items():
        print(f"{cached_file_name}: {cached_file_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Copies files to a cache directory'
        )

    parser.add_argument(
        'path',
        metavar='ImagePath',
        type=str,
        default=config.PIC_DIR,
        nargs="?",
        help='Path to a directory that contains images'
        )
    parser.add_argument(
        '--config-file',
        dest='config',
        type=str,
        default=config.DEFAULT_CONFIG_FILE,
        help='Configuration file holding list of image files'
        )
    parser.add_argument(
        '--cacheroot',
        type=str,
        dest='cachedir',
        action='store',
        default='/media/pi/Expansion Drive',
        help='Root for cached images'
        )
    parser.add_argument(
        '--quantity',
        type=int,
        dest='quantity',
        action='store',
        help='How many files'
        )

    args = parser.parse_args()
    print(args.path,args.config,args.cachedir,args.quantity)

    main(startdir=args.cachedir,
      config_file=args.config,
      number_of_files=args.quantity,
      network_drive_path=args.path
      )

