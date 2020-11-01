#--coding: utf-8 --
#!/usr/bin/python
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
import time 
import random
import pi3d
import argparse
import stat
import json
import math


from PIL import Image, ExifTags, ImageFilter # these are needed for getting exif data from images
from PIL.ExifTags import GPSTAGS,TAGS
from geopy.geocoders import GeoNames

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
#####################################################
# only alter below here if you're keen to experiment!
#####################################################
if KENBURNS:
  kb_up = True
  FIT = False
  BLUR_EDGES = False
if BLUR_ZOOM < 1.0:
  BLUR_ZOOM = 1.0
delta_alpha = 1.0 / (FPS * fade_time) # delta alpha

last_file_change = 0


def get_geotagging(exif): # extract EXIF geographical information
  geotagging = {}
  if config.EXIF_GPS not in exif:
    raise ValueError("Get Geotag: No EXIF geotagging found")
  for (key, val) in config.GPSTAGS.items():
    if key in exif[config.EXIF_GPS]:
      geotagging[val] = exif[config.EXIF_GPS][key]

  return geotagging
    
def get_decimal_from_dms(dms, ref): 

    degrees = dms[0][0] / dms[0][1]
    minutes = dms[1][0] / dms[1][1] / 60.0
    seconds = dms[2][0] / dms[2][1] / 3600.0

    if ref in ['S', 'W']:
        degrees = -degrees
        minutes = -minutes
        seconds = -seconds

    return round(degrees + minutes + seconds, 5)

def get_coordinates(geotags):
    if geotags is not None :
      lat = get_decimal_from_dms(geotags['GPSLatitude'], geotags['GPSLatitudeRef'])
      lon = get_decimal_from_dms(geotags['GPSLongitude'], geotags['GPSLongitudeRef'])
      return (lat,lon)
    else :
      return None

def get_geo_name(exif) : #Obtain geographic names from service provider
  geocoder=geoloc.reverse(get_coordinates(get_geotagging(exif)),10,lang='es') #use your country code for language selection
  return geocoder

def get_orientation(fname) : #extract orientation and capture date from EXIF data
  orientation = 1 
  try:
    im = Image.open(fname) # lazy operation so shouldn't load (better test though)
    exif_data = im._getexif()
    dt = time.mktime(time.strptime(exif_data[config.EXIF_DATID], '%Y:%m:%d %H:%M:%S'))
    orientation = int(exif_data[config.EXIF_ORIENTATION])

  except :  
    dt = os.path.getmtime(fname) # so use file last modified date
  return orientation,dt

  
def tex_load(im, orientation, size):
    
    # change suggested to overcome the out of memory crash of putalpha() with very large images
    (w, h) = im.size
    if w > size[0]: # should really have `from pi3d.Texture import MAX_SIZE` at start
        im = im.resize((size[0], int(h * size[0] / w)))
    elif h > size[0]:
        im = im.resize((int(w * size[0] / h), size[0]))
    im.putalpha(255) # this will convert to RGBA and set alpha to opaque
   
    if orientation == 2:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    if orientation == 3:
        im = im.transpose(Image.ROTATE_180) # rotations are clockwise
    if orientation == 4:
        im = im.transpose(Image.FLIP_TOP_BOTTOM)
    if orientation == 5:
        im = im.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROTATE_270)
    if orientation == 6:
        im = im.transpose(Image.ROTATE_270)
    if orientation == 7:
        im = im.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROTATE_90)
    if orientation == 8:
        im = im.transpose(Image.ROTATE_90)
    if BLUR_EDGES and size is not None:
      wh_rat = (size[0] * im.size[1]) / (size[1] * im.size[0])
      if abs(wh_rat - 1.0) > 0.01: # make a blurred background
        (sc_b, sc_f) = (size[1] / im.size[1], size[0] / im.size[0])
        if wh_rat > 1.0:
          (sc_b, sc_f) = (sc_f, sc_b) # swap round
        (w, h) =  (round(size[0] / sc_b / BLUR_ZOOM), round(size[1] / sc_b / BLUR_ZOOM))
        (x, y) = (round(0.5 * (im.size[0] - w)), round(0.5 * (im.size[1] - h)))
        box = (x, y, x + w, y + h)
        blr_sz = (int(x * 512 / size[0]) for x in size)
        im_b = im.resize(size, resample=0, box=box).resize(blr_sz)
        im_b = im_b.filter(ImageFilter.GaussianBlur(BLUR_AMOUNT))
        im_b = im_b.resize(size, resample=Image.BICUBIC)
        im_b.putalpha(round(255 * config.EDGE_ALPHA))  # to apply the same EDGE_ALPHA as the no blur method.
        im = im.resize((int(x * sc_f) for x in im.size), resample=Image.BICUBIC)
        im_b.paste(im, box=(round(0.5 * (im_b.size[0] - im.size[0])),
                            round(0.5 * (im_b.size[1] - im.size[1]))))
        im = im_b # have to do this as paste applies in place
      do_resize = False
    else:
      do_resize = True
    tex = pi3d.Texture(im, blend=True, m_repeat=True, automatic_resize=do_resize,
                       free_after_load=True)

    return tex

def tidy_name(path_name):
    name = os.path.basename(path_name).upper()
    name = ''.join([c for c in name if c in config.CODEPOINTS])
    return name


def check_changes(dir): #walk the folder structure to check if there are changes
  global last_file_change
  update = False
  for root, _, _ in os.walk(dir):
    try:
        mod_tm = os.stat(root).st_mtime
        if mod_tm > last_file_change:
          last_file_change = mod_tm
          update = True
    except:
        print("Filesystem not available")
        
  return update


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

def timetostring(dot,ticks) :
  if (dot) :
    separator="."
  else :
    separator=" "
  return str(time.localtime(ticks).tm_hour)+separator+str(time.localtime(ticks).tm_min)

def main(
    startdir,                      # Root folder for images, with recursive search
    config_file,                   # File with list of file names (for fast restart)  
    interval,                      # Seconds between images
    shuffle,                       # True or False
    geonamesuser,                  # User name for GeoNames server www.geonames.org
    check_dirs                     # Interval between checking folders in seconds
    ) :

    global paused,geoloc,last_file_change,kb_up,FIT,BLUR_EDGES

    next_check_tm=time.time()+check_dirs
    
    time_dot=True
        
    ##############################################
    # Create GeoNames locator object www.geonames.org
    geoloc=None
    try:
      geoloc=GeoNames(username=geonamesuser)
    except:
      print("Geographic information server not available")
   
    print("Setting up display")
    DISPLAY = pi3d.Display.create(x=0, y=0, frames_per_second=FPS,display_config=pi3d.DISPLAY_CONFIG_HIDE_CURSOR, background=BACKGROUND)
    CAMERA = pi3d.Camera(is_3d=False)
    print(DISPLAY.opengl.gl_id)
    shader = pi3d.Shader(config.PI3DDEMO + "/shaders/blend_new")
    #shader = pi3d.Shader("/home/patrick/python/pi3d_demos/shaders/blend_new")
    slide = pi3d.Sprite(camera=CAMERA, w=DISPLAY.width, h=DISPLAY.height, z=5.0)
    slide.set_shader(shader)
    slide.unif[47] = config.EDGE_ALPHA

    if KEYBOARD:
      kbd = pi3d.Keyboard()

    # images in iFiles list
    nexttm = 0.0
    iFiles, nFi = get_files(startdir,config_file,shuffle)
    next_pic_num = 0
    sfg = None # slide for foreground
    sbg = None # slide for background
    if nFi == 0:
      print('No files selected!')
      exit()

    # PointText and TextBlock. 
    #font = pi3d.Font(FONT_FILE, codepoints=CODEPOINTS, grid_size=7, shadow_radius=4.0,shadow=(128,128,128,12))
    
    grid_size = math.ceil(len(config.CODEPOINTS) ** 0.5)
    font = pi3d.Font(config.FONT_FILE, codepoints=config.CODEPOINTS, grid_size=grid_size, shadow_radius=4.0,shadow=(0,0,0,128))
    text = pi3d.PointText(font, CAMERA, max_chars=200, point_size=50)
    text2 = pi3d.PointText(font, CAMERA, max_chars=8, point_size=50)
    
    
    #text = pi3d.PointText(font, CAMERA, max_chars=200, point_size=50)
    textblock = pi3d.TextBlock(x=-DISPLAY.width * 0.5 + 20, y=-DISPLAY.height * 0.4,
                              z=0.1, rot=0.0, char_count=199,
                              text_format="{}".format(" "), size=0.65, 
                              spacing="F", space=0.02, colour=(1.0, 1.0, 1.0, 1.0))
    text.add_text_block(textblock)
    

    timeblock = pi3d.TextBlock(x=-DISPLAY.width * 0.5 + 20, y=-DISPLAY.height * 0.4 + 10,
                              z=0.1, rot=0.0, char_count=6,
                              text_format="{}".format(" "), size=0.65, 
                              spacing="F", space=0.02, colour=(2.0, 2.0, 2.0, 255.0))
    text2.add_text_block(timeblock)
    
   
   
    #Retrieve last image number to restart the slideshow from config.num file
    #Retrieve next directory check time
    
    cacheddata=(0,0,last_file_change,next_check_tm)
    try:
      with open(config_file+".num",'r') as f:
        cacheddata=json.load(f)
        num_run_through=cacheddata[0]
        next_pic_num=cacheddata[1]
        last_file_change=cacheddata[2]
        next_check_tm=cacheddata[3]
    except:
      num_run_through=0
      next_pic_num=0      
    
    if (next_check_tm < time.time()) :  #if stored check time is in the past, make it "now"
      next_check_tm = time.time()
    print("Start time ",time.strftime(config.TIME_FORMAT,time.localtime()))
    print("Next Check time ",time.strftime(config.TIME_FORMAT,time.localtime(next_check_tm)))
    print("Starting with round number ",num_run_through)
    print("Starting with picture number ",next_pic_num)
    
    tm=time.time()    
    pic_num=next_pic_num
    while DISPLAY.loop_running():
      # use previous time to make spearator blink
      previoustime=tm
      tm = time.time()
    
      if (time.localtime(previoustime).tm_sec > time.localtime(tm).tm_sec) :
        time_dot = not(time_dot)

      #check if there are file to display  
      if nFi > 0:
        
        if (tm > nexttm and not paused) or (tm - nexttm) >= 86400.0: # this must run first iteration of loop
          nexttm = tm + interval
          a = 0.0 # alpha - proportion front image to back
          sbg = sfg
          sfg = None
          while sfg is None: # keep going through until a usable picture is found TODO break out how?
            #print("Fetch new image ",next_pic_num)
            #print("Time until next directory check ",next_check_tm - time.time())
            pic_num = next_pic_num
            next_pic_num += 1
            if next_pic_num >= nFi:
              num_run_through += 1
              next_pic_num = 0
            
            #update persistent cached data for restart
            cacheddata=(num_run_through,pic_num,last_file_change,next_check_tm)
            with open(config_file+".num","w") as f:
              #print("Write to config.num file ", json.dumps(cachedddata))
              json.dump(cacheddata,f,separators=(',',':'))
            
            orientation = 1 # this is default - unrotated
            #coordinates = None
            dt=None
            #include=False
            datestruct=None
            #elapsed=time.time()
            try:
              im = Image.open(iFiles[pic_num])
            except:
              print("Error Opening File",iFiles[pic_num])
              continue
            try:
              exif_data = im._getexif()
            except:
              exif_data=None
            try:        
              orientation = int(exif_data[config.EXIF_ORIENTATION])
            except:
              orientation = 1
            try: 
              dt = time.mktime(time.strptime(exif_data[config.EXIF_DATID], '%Y:%m:%d %H:%M:%S'))
              datestruct=time.localtime(dt)
            except:
              datestruct=None
              #print("No date in EXIF")
            try:
              location = get_geo_name(exif_data)
            except Exception as e: # NB should really check error
              print('Error preparing geoname: ', e)
              location = None
            try:
              sfg = tex_load(im, orientation, (DISPLAY.width, DISPLAY.height))
              #print("Time to prepare and load image into Texture: ",time.time()-elapsed)
            except:
              next_pic_num += 1
              continue
            #print("Have to reset timer!")  
            nexttm = time.time()+interval #reset timer to cope with texture delays
            
          if sbg is None: # first time through
            sbg = sfg
          slide.set_textures([sfg, sbg])
          slide.unif[45:47] = slide.unif[42:44] # transfer front width and height factors to back
          slide.unif[51:53] = slide.unif[48:50] # transfer front width and height offsets
          wh_rat = (DISPLAY.width * sfg.iy) / (DISPLAY.height * sfg.ix)
          if (wh_rat > 1.0 and FIT) or (wh_rat <= 1.0 and not FIT):
            sz1, sz2, os1, os2 = 42, 43, 48, 49
          else:
            sz1, sz2, os1, os2 = 43, 42, 49, 48
            wh_rat = 1.0 / wh_rat
          slide.unif[sz1] = wh_rat
          slide.unif[sz2] = 1.0
          slide.unif[os1] = (wh_rat - 1.0) * 0.5
          slide.unif[os2] = 0.0
          if KENBURNS:
              xstep, ystep = (slide.unif[i] * 2.0 / interval for i in (48, 49))
              slide.unif[48] = 0.0
              slide.unif[49] = 0.0
              kb_up = not kb_up
          overlay_text= "" #this will host the text on screen 
          if SHOW_LOCATION: #(and/or month-year)
            if location is not None:
              overlay_text += tidy_name(str(location))
              #print(overlay_text)
            if datestruct is not None :
              overlay_text += " " + tidy_name(config.MES[datestruct.tm_mon - 1]) + "-" + str(datestruct.tm_year)
              #print(overlay_text)
            try:
              textblock.set_text(text_format="{}".format(overlay_text))
              text.regen()
            except :
              #print("Wrong Overlay_text Format")
              textblock.set_text(" ")

        # print time on screen, blink separator every second
        timetext=timetostring(time_dot,tm)
        timeblock.set_text(text_format="{}".format(timetext))
       

        
        #text.regen()		
        if KENBURNS:
          t_factor = nexttm - tm
          if kb_up:
            t_factor = interval - t_factor
          slide.unif[48] = xstep * t_factor
          slide.unif[49] = ystep * t_factor

        if a < 1.0: # transition is happening
            a += delta_alpha
            slide.unif[44] = a
            
        else: # Check if images have to be re-fetched (no transition on going, so no harm to image
          slide.set_textures([sfg, sfg])
          if (num_run_through > config.NUMBEROFROUNDS) or (time.time() > next_check_tm) : #re-load images after running through them or exceeded time
            print("Refreshing Files list")
            next_check_tm = time.time() + check_dirs  # Set up the next interval
            try:
              if check_changes(startdir): #rebuild files list if changes happened
                print("Re-Fetching images files, erase config file")
                with open(config_file,'w') as f :
                  json.dump('',f) # creates an empty config file, forces directory reload
                iFiles, nFi = get_files(startdir,config_file,shuffle)
                next_pic_num = 0
              else :
                print("No directory changes: do nothing")
            except:
                print("Error refreshing file list, keep old one")
            num_run_through = 0
        
        slide.draw()
        text.draw()
        text2.draw()
      else:
        textblock.set_text("NO IMAGES SELECTED")
        textblock.colouring.set_colour(alpha=1.0)
        text.regen()
        text.draw()
      if KEYBOARD:
        k = kbd.read()
        if k != -1:
          nexttm = time.time() - 86400.0
        if k==27 or quit: #ESC
          break
        if k==ord(' '):
          paused = not paused
        if k==ord('s'): # go back a picture
          next_pic_num -= 2
          if next_pic_num < -1:
            next_pic_num = -1
    try:
      client.loop_stop()
    except Exception as e:
      print("this was going to fail if previous try failed!")
    if KEYBOARD:
      kbd.close()
    DISPLAY.destroy()
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Recursively loads images '
        'from a directory, then displays them in a Slideshow.'
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
        '--waittime',
        type=int,
        dest='waittime',
        action='store',
        default=TIME_DELAY,
        help='Amount of time to wait before showing the next image.'
        )
    parser.add_argument(
        '--shuffle',
        type=bool,
        dest='shuffle',
        action='store',
        default=True,
        help='Shuffle pictures list'
        )
    parser.add_argument(
        '--geouser',
        type=str,
        dest='geouser',
        action='store',
        default=config.GEONAMESUSER,
        help='User Name for GeoNames server'
        )
    parser.add_argument(
        '--dir-check',
        type=float,
        dest='dirchecktm',
        action='store',
        default=config.CHECK_DIR_TM,
        help='Interval between check directories'
        )

    args = parser.parse_args()
    print(args.path,args.config,args.waittime,"Shuffle ",args.shuffle)

    main(startdir=args.path,
      config_file=args.config,
      interval=args.waittime,
      shuffle=args.shuffle,
      geonamesuser=args.geouser,
      check_dirs=args.dirchecktm
      )


