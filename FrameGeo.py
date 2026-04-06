#!/usr/bin/env python3
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
import argparse
import json
import logging
import math
import os
import random
import shutil
import signal
import subprocess
import time
import tempfile

import exif
from geopy.geocoders import GeoNames
from PIL import Image, ImageFilter  # these are needed for getting exif data from images
import pi3d
import setproctitle  # to set process title
import threading

import FrameConfig as config

def atomic_write_json(path, data):
    """
    Escribe un JSON de forma atómica:
    - escribe en un fichero temporal en el mismo directorio
    - fsync
    - os.replace() sobre el destino
    Así evitamos JSON corrupto si hay corte de luz o crash.
    """
    dir_name = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, separators=(',', ':'))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        # Si algo va mal, intentamos eliminar el temporal
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

scan_thread = None
scan_in_progress = False
scan_result = None
scan_fs_state= None
current_fs_state = None
scan_lock = threading.Lock()
scan_ready_event = threading.Event()

# Set process title
setproctitle.setproctitle("FrameGeo")

##################### SETUP SIGNAL HANDLING ########################
# Set up signal handling to catch Ctrl-C and other signals
def signal_handler(signal, frame):
    logger.info("Signal %d received, exiting...", signal)
    os.system(CMD_SCREEN_OFF)  # turn screen off
    save_geo_cache()
    exit(0)
if config.PLATFORM != "Windows":    
  signal.signal(signal.SIGINT, signal_handler)  # Catch Ctrl-C
  signal.signal(signal.SIGTERM, signal_handler)  # Catch termination signal
  signal.signal(signal.SIGHUP, signal_handler)  # Catch hangup signal
  signal.signal(signal.SIGQUIT, signal_handler)  # Catch quit signal

#####################################################################

if config.PLATFORM == "Raspberry Pi":
  CMD_SCREEN_OFF = 'xset -d :0 dpms force off ; xset -d :0 dpms 60 300 300'
  CMD_SCREEN_ON = 'xset -d :0 dpms force on s off ; xset -d :0 dpms 20000 20000 20000'
else :
  CMD_SCREEN_OFF = ''
  CMD_SCREEN_ON = ''

#############################
SHOW_LOCATION = True
GEO_CACHE_FILE = config.TEMPDIR + "/framegeo_geocache.json"
geo_cache = {}
geo_cache_dirty = False
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
fade_time = 0.3
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

CW = 0 # Clockwise rotation
CCW = 1 # Counterclockwise rotation
Rotation=[{1:6,2:7,3:8,4:5,5:2,6:3,7:4,8:1},{1:8,2:5,3:6,4:7,5:4,6:1,7:2,8:3}] #Transformations to rotate pictures (see below)
""" if (sense == CW) :
    if (old_orientation == 1) :   #upright
      new_orientation = 6         # set to rotate 90CW
    elif (old_orientation == 2) : # Mirror horizontal
      new_orientation = 7         # set to Mirror Horizontal rotated 90 CW
    elif (old_orientation == 3) : # rotate 180
      new_orientation = 8         # set to rotate 270 CW
    elif (old_orientation == 4) : # Mirror Vertical
      new_orientation = 5         # set to mirror horizontal and rotate 270 CW
    elif (old_orientation == 5) : # mirror horizontal and rotate 270 CW
      new_orientation = 2         # set to mirror horizontal
    elif (old_orientation == 6) : # Rotate 90 CW
      new_orientation = 3         # set to rotate 180
    elif (old_orientation == 7) : # Mirror horizontal and rotate 90CW
      new_orientation = 4         # set to mirror vertical
    elif (old_orientation == 8) : # Rotate 270 CW
      new_orientation = 1         # set to upright
  elif (sense==CCW):
    if (old_orientation == 1) :   #upright
      new_orientation = 8         # set to rotate 90CCW/270CW
    elif (old_orientation == 2) : # Mirror horizontal
      new_orientation = 5         # set to Mirror Horizontal rotated 90CCW/270CW
    elif (old_orientation == 3) : # rotate 180
      new_orientation = 6         # set to rotate 90CW/270CCW
    elif (old_orientation == 4) : # Mirror Vertical
      new_orientation = 7         # set to mirror horizontal and rotate 90CW
    elif (old_orientation == 5) : # mirror horizontal and rotate 270 CW
      new_orientation = 4         # set to mirror vertical
    elif (old_orientation == 6) : # Rotate 90 CW
      new_orientation = 1         # set to upright
    elif (old_orientation == 7) : # Mirror horizontal and rotate 90CW
      new_orientation = 2         # set to mirror horizontal
    elif (old_orientation == 8) : # Rotate 270 CW
      new_orientation = 3         # set to rotate 180
 """

if config.BUTTONS and config.PLATFORM == "Raspberry Pi":
  from gpiozero import Button
  Button.estado=0 #idle

  """
   Button state is linked to the action taken
   0= Idle 
   1=was pressed, not yet attended
   2=was held, not yet attended. 
   Transition Table
   State / Event
             Press    Hold    Release After Action
   Idle      Pressed  Held    Idle    N/A
   Pressed   Pressed  Pressed Pressed Idle
   Held      Pressed  Held    Held    Idle
  """

last_file_change = 0

def launchTiempo(delay,scanner=None,wait=None) :
  global scan_in_progress
  poll_interval=0.1
  #proc=subprocess.Popen(['surf','-F','https://www.aemet.es/es/eltiempo/prediccion/municipios/alcala-de-henares-id28005'])
  proc=subprocess.Popen([config.BROWSER,'--kiosk','https://www.aemet.es/es/eltiempo/prediccion/municipios/alcala-de-henares-id28005'])
  logger.info("Launch Weather Forecast with pid %d",proc.pid)
  
  if config.PLATFORM == "Raspberry Pi":
    time.sleep(30)
    subprocess.Popen([config.KEYCOMM,'key','Down','Down','Down','Down','mousemove','0','0'])
  
  if scanner is not None:
    start=time.monotonic()
    while True:
      if not scan_in_progress:
        break
      if wait is not None:
        elapsed=time.monotonic()-start
        if elapsed > wait:
          break
      time.sleep(poll_interval)
  time.sleep(delay)
  os.kill(proc.pid, signal.SIGTERM)
  logger.info("process %d killed",proc.pid)

def launchSolar(delay,scanner=None,wait=None) :
  global scan_in_progress
  poll_interval=0.1
  proc=subprocess.Popen([config.BROWSER,'--kiosk','http://pi4.local:1880/ui'])
  subprocess.Popen([config.KEYCOMM,'mousemove','0','0'])
  logger.info("Launch Solar Production with pid %d",proc.pid)
  
  if scanner is not None:
    start=time.monotonic()
    while True:
      if not scan_in_progress:
        break
      if wait is not None:
        elapsed=time.monotonic()-start
        if elapsed > wait:
          break
      time.sleep(poll_interval)
  time.sleep(delay)
    
  os.kill(proc.pid, signal.SIGTERM)
  logger.info("process %d killed",proc.pid)

#########################################################
# Geolocalization 
def save_geo_cache() :
  global geo_cache_dirty
  if geo_cache_dirty:
        try:
            with open(GEO_CACHE_FILE, "w") as f:
              json.dump(geo_cache, f, indent=2)
              logger.info("Geo cache saved: %d entries", len(geo_cache))
        except Exception as e:
          logger.warning("Could not save geo cache: %s", str(e))

def get_geotagging(exif): # extract EXIF geographical information
  geotagging = {}
  if config.EXIF_GPS not in exif:
    raise ValueError("Get Geotag: No EXIF geotagging found")
  for (key, val) in config.GPSTAGS.items():
    if key in exif[config.EXIF_GPS]:
      geotagging[val] = exif[config.EXIF_GPS][key]

  return geotagging
    
def get_decimal_from_dms(dms, ref): 

    degrees = dms[0]
    minutes = dms[1] / 60.0
    seconds = dms[2] / 3600.0

    if ref in ['S', 'W']:
        degrees = -degrees
        minutes = -minutes
        seconds = -seconds

    return round(degrees + minutes + seconds, 5)

def get_coordinates(geotags):
    if geotags is not None :
      lat = get_decimal_from_dms(geotags['GPSLatitude'], geotags['GPSLatitudeRef'])
      lon = get_decimal_from_dms(geotags['GPSLongitude'], geotags['GPSLongitudeRef'])
      logger.info('coordinates= %f %f',lat,lon)
      return (lat,lon)
    else :
      return None

# def get_geo_name(exif) : #Obtain geographic names from service provider
#   # geocoder=geoloc.reverse(get_coordinates(get_geotagging(exif)),timeout=10,language='es') 
#   geocoder=geoloc.reverse(get_coordinates(get_geotagging(exif)),timeout=10,lang='es') 
#   return geocoder

def get_geo_name(exif_data):
    global geo_cache, geo_cache_dirty

    coords = get_coordinates(get_geotagging(exif_data))
    if coords is None or geoloc is None:
        return None

    # 🔑 normalización: ~100 m
    lat = round(coords[0], 3)
    lon = round(coords[1], 3)
    key = f"{lat},{lon}"

    # ✅ CACHE HIT
    if key in geo_cache:
        logger.info("Geo cache hit: %s", key)
        return geo_cache[key]

    try:
        loc = geoloc.reverse(
            (lat, lon),
            exactly_one=True,
            timeout=10,
            lang="es"
        )
        if not loc:
            return None

        raw = loc.raw or {}

        # GeoNames devuelve campos planos
        city = raw.get("name")
        region = raw.get("adminName1")
        country = raw.get("countryName")

        parts = [p for p in (city, region, country) if p]
        text = ", ".join(parts) if parts else None

        if text:
            geo_cache[key] = text
            geo_cache_dirty = True

        return text

    except Exception as e:
        logger.warning("GeoNames reverse failed: %s", str(e))
        return None

#################################################

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
  


####################################################
# New scan files + fill files list on separate Thread
#######################################################
def scan_files_thread(startdir, shuffle, filelist_cache):
    """
    Hilo en background que:
      - recorre el árbol de directorios
      - construye la lista de imágenes (new_files)
      - calcula fingerprint del FS (dir_count, file_count, max_mtime)
      - persiste un snapshot coherente (fs + files) en filelist_cache
      - deja el resultado en scan_result / scan_fs_state para que
        el hilo principal haga el swap cuando quiera.
    """
    global scan_result, scan_in_progress, scan_fs_state
    scan_in_progress = True
    logger.info("Background scan started in %s", startdir)

    new_files = []
    dir_count = 0
    file_count = 0
    max_mtime = 0.0

    extensions = ['.png', '.jpg', '.jpeg', '.bmp']

    for root, _dirnames, filenames in os.walk(startdir):
        dir_count += 1

        # mtime del directorio
        try:
            mtime_dir = os.stat(root).st_mtime
            if mtime_dir > max_mtime:
                max_mtime = mtime_dir
        except Exception:
            pass

        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext in extensions and not filename.startswith('.') and '.AppleDouble' not in root:
                path = os.path.join(root, filename)
                new_files.append(path)
                file_count += 1

                # mtime del fichero
                try:
                    mtime_file = os.stat(path).st_mtime
                    if mtime_file > max_mtime:
                        max_mtime = mtime_file
                except Exception:
                    pass

                # opcional: log de progreso si hay MUCHOS ficheros
                if file_count % 1000 == 0:
                    logger.info("Scanned %d image files so far...", file_count)

    # Ordenación / shuffle
    if shuffle:
        random.shuffle(new_files)
    else:
        new_files.sort()

    # Fingerprint del filesystem
    fingerprint = (startdir,dir_count, file_count, max_mtime)

    # Construir snapshot para persistir en disco
    snapshot = {
        "version": 1,
        "created": time.time(),
        "fs": {
            "fingerprint": fingerprint
        },
        "files": new_files
    }

    # Persistencia atómica del snapshot
    try:
        atomic_write_json(filelist_cache, snapshot)
        logger.info("File list snapshot written to %s", filelist_cache)
    except Exception as e:
        logger.warning("Could not write file list snapshot: %s", str(e))

    # Publicar resultado en las variables compartidas
    with scan_lock:
        scan_result = new_files
        scan_fs_state = fingerprint
        scan_in_progress = False

    # Señalar que (al menos) este scan ha terminado
    scan_ready_event.set()

    logger.info(
        "Background scan finished: %d files, %d dirs, max_mtime=%.0f",
        file_count, dir_count, max_mtime
    )
    
def snapshot_is_usable(snapshot, fs_state, rootfolder, max_age_seconds):
    """
    Devuelve True si el snapshot puede reutilizarse:
    - snapshot no es None
    - fingerprint coincide
    - snapshot no es demasiado viejo (opcional)
    - coincide el directorio de los archivos con el snapshot
    """
    if not snapshot:
        return False
    if not fs_state:
        return False

    snap_fp = snapshot.get("fs", {}).get("fingerprint")
    if snap_fp != fs_state.get("fingerprint"):
        return False
    # Comprueba que el snapshot apunta al mismo directorio que los parámetros
    if snap_fp[0] != rootfolder:
      return False
    # Comprobación opcional por antigüedad:
    snap_time = snapshot.get("created")
    if snap_time is None:
        return False

    if time.time() - snap_time > max_age_seconds:
        return False

    return True

def save_file(filename) : # Makes a copy of the file to a Backup folder
  stripped_filename = os.path.basename(filename)
  dest_filename = backup_dir + "/" + stripped_filename
  if not os.path.exists(backup_dir) : # create backup folder if it does not exist
    logger.info("Create Backup Folder: %s", backup_dir) 
    os.mkdir(backup_dir)
  if not os.path.exists(dest_filename) :# check if there is already a copy saved in backup
    logger.info("copying %s to %s",stripped_filename,config.BKUP_DIR)
    shutil.copy2(filename,dest_filename)
    
def timetostring(dot,ticks):
  if (dot) :
    separator=":"
  else :
    separator=" "
  minutes = str(time.localtime(ticks).tm_min)
  hour = str(time.localtime(ticks).tm_hour)
  if int(hour) < 10 : 
    hour = "0"+hour
  if int(minutes) < 10 :
    minutes ="0"+minutes
  return hour+separator+minutes


def handle_press(btn) :
    logger.info("Button pressed, estado actual %r",btn.estado)
    if btn.estado==0 :
      btn.estado=1
      logger.info("Nuevo Estado %r",btn.estado)
   
def handle_hold(btn) :
    logger.info("button held, estado actual %r",btn.estado)
    if btn.estado==0 or btn.estado == 1:
      btn.estado=2
      logger.info("Nuevo Estado %r",btn.estado)
      
def main(
    startdir,                      # Root folder for images, with recursive search
    config_file,                   # File with list of file names (for fast restart)  
    interval,                      # Seconds between images
    shuffle,                       # True or False
    geonamesuser,                  # User name for GeoNames server www.geonames.org
    check_dirs,                    # Interval between checking folders in seconds
    weathertime,                    # Time to show weather forecast in seconds
    logfile,                      # Log file name
    debug,              # Debug mode
    ) :
        
    slide_state = "loading"
    global backup_dir,paused,geoloc,last_file_change,kb_up,screen,logger,scan_result,scan_in_progress,scan_fs_state
  # Set up logging      
    if debug:
        loglevel=logging.DEBUG
    else:
        loglevel=logging.INFO
    
    from logging.handlers import RotatingFileHandler
     
    logging.basicConfig (
    level=loglevel,  # Set the logging level
    format='%(pathname)s: %(asctime)s - %(levelname)s:%(message)s',  # Customize log format
            datefmt='%m/%d/%Y %I:%M:%S %p',
    handlers=[RotatingFileHandler(logfile, maxBytes=10*1024*1024, backupCount=5)]
    )
    logger=logging.getLogger(__name__)
    
    logger.info("Starting FrameGeo with parameters: startdir=%s,config_file=%s,interval=%d,shuffle=%s,geonamesuser=%s,check_dirs=%d,weathertime=%d,logfile=%s",
                startdir,
                config_file,
                interval,
                shuffle,
                geonamesuser,
                check_dirs,
                weathertime,
                logfile)
    
    backup_dir = config.BKUP_DIR
    
    logger.info(backup_dir)

    if config.BUTTONS:
      pause_button = Button(8, hold_time=20,bounce_time=2)
      back_button = Button(9,hold_time=6,bounce_time=2)
      forward_button = Button(4,hold_time=6,bounce_time=2)
      rotateCW_button = Button(6,hold_time=6,bounce_time=2)
      rotateCCW_button = Button(5,hold_time=6,bounce_time=2)

      pause_button.when_pressed = handle_press
      back_button.when_pressed = handle_press
      pause_button.when_held=handle_hold
      back_button.when_held=handle_hold
      forward_button.when_pressed=handle_press
      forward_button.when_held=handle_hold

      rotateCW_button.when_pressed= handle_press
      rotateCW_button.when_held=handle_hold
      rotateCCW_button.when_pressed= handle_press
      rotateCCW_button.when_held=handle_hold
 
    paused=False
    next_check_tm=time.time()+check_dirs
    time_dot=True
    screen = True 

    ##############################################
    # Setup cache for gelocation information
    global geo_cache, geo_cache_dirty

    try:
      if os.path.exists(GEO_CACHE_FILE):
        with open(GEO_CACHE_FILE, "r") as f:
            geo_cache = json.load(f)
        logger.info("Geo cache loaded: %d entries", len(geo_cache))
      else:
        geo_cache = {}
    except Exception as e:
      logger.warning("Could not load geo cache: %s", str(e))

    geo_cache_dirty = False
    # Create GeoNames locator object www.geonames.org    
    geoloc=None
    try:
      geoloc=GeoNames(username=geonamesuser)
    except:
      logger.error("Geographic information server not available")
    
    #####################################################
    # --- Estado inicial y lectura de persistencia ---

    global current_fs_state, scan_in_progress, scan_thread

    # Estado por defecto
    iFiles = []
    nFi = 0
    num_run_through = 0
    next_pic_num = 0
    next_check_tm = time.time() + check_dirs
    fs_state = None
    file_snapshot = None
    run_config_file = config_file + ".num"
    content_config_file = config_file + ".files.json"
    SNAPSHOT_MAX_AGE = 24 * 3600   # 24 horas
    scan_result=None
    nexttm=0
    scan_fs_state=None
    scan_in_progress=False  
    
    # 1) Leer estado persistente de ejecución + FS desde config_file + ".num"
    try:
        with open(run_config_file, "r") as f:
            data = json.load(f)
            runtime_state = data.get("runtime", {})
            fs_state = data.get("fs", None)

            num_run_through = runtime_state.get("num_run_through", 0)
            next_pic_num = runtime_state.get("next_pic_num", 0)
            next_check_tm = runtime_state.get("next_check_tm", time.time() + check_dirs)

            logger.info(
                "Restored runtime state: run=%d pic=%d",
                num_run_through,
                next_pic_num,
            )
    except Exception as e:
        logger.info("No previous runtime state restored (%s)", str(e))
        fs_state = None

    # 2) Leer snapshot de iFiles desde FILELIST_CACHE
    try:
        with open(content_config_file, "r") as f:
            file_snapshot = json.load(f)
        logger.info(
            "Loaded file snapshot: %d entries",
            len(file_snapshot.get("files", []))
        )
    except Exception as e:
        logger.info("No valid file snapshot found (%s)", str(e))
        file_snapshot = None

    # 3) Decidir si reutilizar snapshot o hacer escaneo inicial
    if snapshot_is_usable(file_snapshot, fs_state, startdir, SNAPSHOT_MAX_AGE):
        logger.info("Reusing existing iFiles snapshot")
        iFiles = file_snapshot["files"]
        nFi = len(iFiles)
        if nFi == 0:
            logger.warning("Snapshot is empty, forcing initial scan")
            reuse_snapshot = False
        else:
            # Asegurar que next_pic_num está dentro de rango
            if next_pic_num < 0 or next_pic_num >= nFi:
                next_pic_num = 0
            reuse_snapshot = True
            current_fs_state = fs_state
    else:
        logger.info("Snapshot invalid or outdated — initial scan required")
        reuse_snapshot = False

    # 4) Si no se puede reutilizar snapshot, lanzar escaneo inicial en background
    if not reuse_snapshot:
        logger.info("Launching initial background scan")
        scan_in_progress = True
        scan_ready_event.clear()
        scan_thread = threading.Thread(
            target=scan_files_thread,
            args=(startdir, shuffle, content_config_file),
            daemon=True
        )
        scan_thread.start()
        
    logger.info("Setting up display")
    if config.PLATFORM in ("Linux","Windows"):
      DISPLAY = pi3d.Display.create(
                w=1280, h=1080,
                x=0, y=0,
                frames_per_second=FPS,
                window_title="FrameGeo",
                display_config=pi3d.DISPLAY_CONFIG_DEFAULT,
                background=BACKGROUND
                )
    else: 
      DISPLAY = pi3d.Display.create(x=0, y=0,
                                    frames_per_second=FPS,
                                    display_config=pi3d.DISPLAY_CONFIG_HIDE_CURSOR,
                                    background=BACKGROUND)
    logger.info("DISPLAY size: %d x %d", DISPLAY.width, DISPLAY.height)
    CAMERA = pi3d.Camera(is_3d=False)
    logger.info(DISPLAY.opengl.gl_id)
    shader = pi3d.Shader(config.PI3DDEMO + "/shaders/blend_new")
    slide = pi3d.Sprite(camera=CAMERA, w=DISPLAY.width, h=DISPLAY.height, z=5.0)
    slide.set_shader(shader)
    slide.unif[47] = config.EDGE_ALPHA
    os.system(CMD_SCREEN_ON) #turn screen on
    logger.info("Screen ON")
    
    if weathertime != 0:
      logger.info("launching weather forecast and solar production status")
      launchTiempo(weathertime/2,scanner=scan_thread,wait=weathertime) # show weather forecast for weathertime/2 seconds 
      launchSolar(weathertime/2,scanner=scan_thread) # show status of solar production for (weathertime/2) seconds
        
          
    # 5) Si hubo escaneo inicial en background, asegurarse de que ha terminado
    if not reuse_snapshot:
        if not scan_ready_event.is_set():
            logger.info("Waiting for initial file scan to complete after Firefox screens")
            scan_ready_event.wait()

        # Aplicar resultado del escaneo inicial
        with scan_lock:
            if scan_result is not None:
                iFiles = scan_result
                nFi = len(iFiles)
                current_fs_state = {"fingerprint": scan_fs_state}
                scan_result = None
                num_run_through = 0
                next_pic_num = 0
                next_check_tm=time.time()+check_dirs
                logger.info("Initial file list applied: %d images", nFi)

        # Persistir nuevo estado runtime + fs
        try:
            state_data = {
                "runtime": {
                    "num_run_through": num_run_through,
                    "next_pic_num": next_pic_num,
                    "next_check_tm": next_check_tm,
                },
                "fs": current_fs_state,
            }
            with open(run_config_file, "w") as f:
                json.dump(state_data, f, separators=(',', ':'))
            snapshot = {
                        "version": 1,
                        "created": time.time(),
                        "fs": current_fs_state,
                        "files": iFiles
                        }
            atomic_write_json(content_config_file, snapshot)
            logger.info("Initial snapshot written (%d entries)", nFi)
        except Exception as e:
          logger.warning("Could not persist runtime/fs state: %s", str(e))
    
    kbd=None
    if KEYBOARD:
      kbd = pi3d.Keyboard()


      # Ensure initial scan has completed before slideshow starts

    sfg = None # slide for foreground
    sbg = None # slide for background
    
   # 6) Comprobar que hay imágenes
    if nFi == 0:
        logger.error('No image files found!')
        os.system(CMD_SCREEN_OFF)
        DISPLAY.destroy()
        return
    
  
    
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
    
    timeblock = pi3d.TextBlock(x=DISPLAY.width*0.5 - 150, y=DISPLAY.height * 0.5 - 50,
                              z=0.1, rot=0.0, char_count=6,
                              text_format="{}".format(" "), size=0.65, 
                              spacing="F", space=0.02, colour=(1.0, 1.0, 1.0, 1.0))
    text2.add_text_block(timeblock)
       
    if (next_check_tm < time.time()) :  #if stored check time is in the past, make it "now"
      next_check_tm = time.time()+check_dirs
    logger.info("Start time %s",time.strftime(config.TIME_FORMAT,time.localtime()))
    logger.info("Next Check time %s",time.strftime(config.TIME_FORMAT,time.localtime(next_check_tm)))
    logger.info("Starting with round number %d",num_run_through)
    logger.info("Starting with picture number %d",next_pic_num)
    
    tm=time.time()    
    pic_num=next_pic_num
    # Main loop 
    
    while DISPLAY.loop_running() :
      # PREPARATION
      previous = tm # record previous time value, used to make cursor blink
      tm = time.time()
      if weathertime != 0 :
      # check if at the top of the hour
        if (time.localtime(tm).tm_min == 60 - (weathertime // 60)) :
          logger.info("Launching weather forecast")
          launchTiempo(weathertime) #show weather forecast for weathertime seconds
        elif (time.localtime(tm).tm_min == 30 - (weathertime //60)) :
          logger.info("Launching solar production status")
          launchSolar(weathertime) # show status of solar production for weathertime seconds
      # after that, continue with slide show
      # Solve time display 
      # print time on screen, blink separator every second
      if (time.localtime(previous).tm_sec < time.localtime(tm).tm_sec) : #blink dot
        time_dot = not(time_dot)
      if not paused :
        timetext=timetostring(time_dot,tm)
      else :
        timetext="PAUSA"
      # regardless of state, handle ujser input: Keyboard and Buttons
      if KEYBOARD:
        k = kbd.read()
        if k != -1:
          logger.debug("Key pressed", tm-nexttm)
          if k==27 or quit: #ESC
            break
          if k==ord('b'):
            logger.info("Toggle Screen on/off")
            if screen:
              os.system(CMD_SCREEN_OFF)
            else:
              os.system(CMD_SCREEN_ON)
            screen=not screen
            logger.info("Screen ON %s",screen)
          if k==ord(' '):
            paused = not paused
          if k==ord('s'): # go back a picture
            nexttm = 0
            next_pic_num -= 2
            if next_pic_num < -1:
              next_pic_num = -1
            nexttm = delta
          if k==ord('q'): #go forward
            nexttm = delta

          if k==ord('r') and paused: # rotate picture (only if paused)
            nexttm = delta
            im.close() #close file on disk
            try:
                with open(iFiles[pic_num],'rb') as tmp_file: #open file again to be used in exif context
                  tmp_im = exif.Image(tmp_file)
                  tmp_file.close() 
                  if (tmp_im.has_exif) : # If it has exif data, rotate it if it does not, do nothing
                    save_file(iFiles[pic_num]) # Copy file to Backup folder
                    tmp_im.orientation = Rotation[CCW][tmp_im.orientation] # changes EXIF data orientation parameter              
                    with open(iFiles[pic_num],'wb') as tmp_file: # Write the file with new exif orientation
                      tmp_file.write(tmp_im.get_file())
                    next_pic_num -=1 # force reload on screen
            except:
                logger.error("Error when rotating photo")
            #    nexttm = delta

          if k==ord('t') and paused: # rotate picture (only if paused)
            nexttm = delta
            im.close() #close file on disk
            try:
                with open(iFiles[pic_num],'rb') as tmp_file: #open file again to be used in exif context
                  tmp_im = exif.Image(tmp_file)
                  tmp_file.close() 
                  if (tmp_im.has_exif) : # If it has exif data, rotate it if it does not, do nothing
                    save_file(iFiles[pic_num]) # Copy file to Backup folder
                    tmp_im.orientation = Rotation[CW][tmp_im.orientation] # changes EXIF data orientation parameter              
                    with open(iFiles[pic_num],'wb') as tmp_file: # Write the file with new exif orientation
                      tmp_file.write(tmp_im.get_file())
                    next_pic_num -=1 # force reload on screen
            except:
                logger.error("Error when rotating photo")
    
      if config.BUTTONS:
  #Handling of config.BUTTONS goes here
        if paused and (rotateCW_button.estado == 1 or rotateCW_button.estado == 2): # Need to be on pause 
            rotateCW_button.estado = 0
            nexttm = delta
            im.close() #close file on disk
            try:
                with open(iFiles[pic_num],'rb') as tmp_file: #open file again to be used in exif context
                  tmp_im = exif.Image(tmp_file)
                  tmp_file.close() 
                  if (tmp_im.has_exif) : # If it has exif data, rotate it if it does not, do nothing
                    save_file(iFiles[pic_num]) # Copy file to Backup folder
                    tmp_im.orientation =  Rotation[CW][tmp_im.orientation] # changes EXIF data orientation parameter
                    with open(iFiles[pic_num],'wb') as tmp_file: # Write the file with new exif orientation
                      tmp_file.write(tmp_im.get_file())
                    next_pic_num -=1 # force reload on screen
            except:
                logger.error("Error when rotating photo")
        else :
            rotateCW_button.estado = 0

        if paused and (rotateCCW_button.estado == 1 or rotateCCW_button.estado == 2): # Need to be on pause 
            rotateCCW_button.estado = 0
            nexttm = delta
            im.close() #close file on disk
            try:
                with open(iFiles[pic_num],'rb') as tmp_file: #open file again to be used in exif context
                  tmp_im = exif.Image(tmp_file)
                  tmp_file.close() 
                  if (tmp_im.has_exif) : # If it has exif data, rotate it if it does not, do nothing
                    save_file(iFiles[pic_num]) # Copy file to Backup folder
                    tmp_im.orientation = Rotation[CCW][tmp_im.orientation] # changes EXIF data orientation parameter              
                    with open(iFiles[pic_num],'wb') as tmp_file: # Write the file with new exif orientation
                      tmp_file.write(tmp_im.get_file())
                    next_pic_num -=1 # force reload on screen
            except:
                logger.error("Error when rotating photo")
        else :
            rotateCCW_button.estado = 0
                
        if pause_button.estado == 1: # button was pressed
          paused = not paused
          pause_button.estado = 0
  
        if pause_button.estado == 2: # pause button held: toggle screen on/off
          if screen:
            os.system(CMD_SCREEN_OFF)
          else:
            os.system(CMD_SCREEN_ON)
          screen=not screen
          pause_button.estado = 0
          logger.info("Toggle Screen ON/OFF %s",screen)

        if back_button.estado == 1 or back_button.estado == 2 : 
          nexttm = delta
          next_pic_num -= 2
          if next_pic_num < -1:
            next_pic_num = -1
          #nexttm = 0 #force reload
          back_button.estado = 0
        if forward_button.estado == 1 or forward_button.estado == 2 : 
          nexttm = delta
          forward_button.estado = 0
# All config.BUTTONS go to idle after processing them, regardless of state
      #continue preparation
      timeblock.set_text(text_format="{}".format(timetext))
      if (tm > nexttm and not paused) or ((tm - nexttm) >= check_dirs): # this must run first iteration of loop
        logger.debug("tm es %d; nexttm es %d; la resta %d",tm,nexttm,tm-nexttm)
        slide_state="loading"
        logger.debug("Going to %s",slide_state)
      
      # Lanzar rescan periódico si toca
      if time.time() > next_check_tm and not scan_in_progress:
          logger.info("Launching periodic background scan")
          scan_in_progress = True
          scan_ready_event.clear()   # opcional
          threading.Thread(
              target=scan_files_thread,
              args=(startdir, shuffle, content_config_file),
              daemon=True
          ).start()
        
      # State machine implementation
      match slide_state :
        case "loading":
      #check if there are files to display  
          #if nFi > 0:
          # If needed, display new photo
          
          nexttm = tm + interval
          a = 0.0 # alpha - proportion front image to back
          sbg = sfg # previous photo stored for transition
          sfg = None #Next photo to be loaded
          attempts= 0
          location=None  
          datestruct=None         
          im=None
          while sfg is None and attempts < 5: # keep going through until a usable picture is found 
        # Calculate next picture index to be shown
            attempts += 1
            pic_num = next_pic_num
            next_pic_num += 1
            if next_pic_num >= nFi: # detect if a refresh is needed on the file list
              num_run_through += 1
              next_pic_num = 0
     
            # File Open and texture build 
            try:
              temp=time.time()
              im = Image.open(iFiles[pic_num])
              logger.info("foto numero %d %s",pic_num,iFiles[pic_num])
            except Exception as e:
              logger.error("Error Opening File: %s: %s",e,iFiles[pic_num])
              continue
            # EXIF data and geolocation analysis
            # define some default values
            orientation = 1 # unrotated
            dt=None         # will hold date from EXIF
            datestruct=None # will hold formatted date w
            # Format metadata
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
            try:
              location = get_geo_name(exif_data)
              save_geo_cache()
            
            except Exception as e: # NB should really check error
              logger.warning('Error preparing geoname: %s',str(e))
              location = None
            # Load and format image
            try:
              win_w = DISPLAY.width
              win_h = DISPLAY.height

              if win_w <= 0 or win_h <= 0:
                  # Tamaño por defecto razonable para Windows
                  win_w, win_h = 1280, 720
                  logger.warning(
                      "DISPLAY size reported as %d x %d, using fallback %d x %d",
                      DISPLAY.width, DISPLAY.height, win_w, win_h
                  )
              sfg = tex_load(im, orientation, (win_w, win_h))
            except Exception as e:
                  sfg = None
                  logger.warning("Error loading texture: %s", str(e))
                  continue
          if im is None: #Failed to load after 5 attempts, move on
            logger.error("Error Opening File %s",iFiles[pic_num])
            continue
               
          nexttm = tm+interval #Time points to next interval 
          
  
# Prepare the different texts to be shown
          overlay_text= "" #this will host the text on screen 
          if SHOW_LOCATION: #(and/or month-year)
            if location is not None:
              overlay_text += tidy_name(str(location))
              logger.debug(overlay_text)
            if datestruct is not None :
              overlay_text += " " + tidy_name(config.MES[datestruct.tm_mon - 1]) + "-" + str(datestruct.tm_year)
              logger.debug(overlay_text)
            try:
              textblock.set_text(text_format="{}".format(overlay_text))
              text.regen()
            except :
              logger.warning("Wrong Overlay_text Format")
              textblock.set_text(" ")
              
          
        #Prepare Image Rendering            
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
          slide_state = "transition"
          logger.debug("Going to %s",slide_state)

        case "transition":
            # manages transition
          if KENBURNS:
            xstep, ystep = (slide.unif[i] * 2.0 / interval for i in (48, 49))
            slide.unif[48] = 0.0
            slide.unif[49] = 0.0
            kb_up = not kb_up
          #if KENBURNS:
            t_factor = nexttm - tm
            if kb_up:
              t_factor = interval - t_factor
            slide.unif[48] = xstep * t_factor
            slide.unif[49] = ystep * t_factor
          slide.set_textures([sfg, sbg])
          a += delta_alpha
          slide.unif[44] = a
          slide.draw()
          text.draw()
          text2.draw()
          if a >= 1.0:
            slide.set_textures([sfg, sfg])
            sbg = sfg
            slide_state = "display"
            logger.debug("Going to %s",slide_state)
          # State: DISPLAY
        case "display":
          #render the image
          slide.draw()
          #render the text
          text.draw()
          text2.draw()
          # --- Actualización periódica: aplicar nuevo snapshot si el scan terminó ---
          with scan_lock:
            if scan_result is not None:
                logger.info("Applying background rescan result")

                # 1. Swap de la nueva lista
                iFiles = scan_result
                nFi = len(iFiles)
                scan_result = None

                # Reiniciar posicionamiento para que slideshow sea coherente
                next_pic_num = 0
                num_run_through = 0

                # 2. Actualizar fingerprint del filesystem
                current_fs_state = {"fingerprint": scan_fs_state}

                # 3. Persistir runtime + FS en .num
                try:
                    state_data = {
                        "runtime": {
                            "num_run_through": num_run_through,
                            "next_pic_num": next_pic_num,
                            "next_check_tm": next_check_tm,
                        },
                        "fs": current_fs_state,
                    }
                    with open(run_config_file, "w") as f:
                        json.dump(state_data, f, separators=(',', ':'))
                except Exception as e:
                    logger.warning("Could not persist .num state after rescan: %s", str(e))

                # 4. Persistir snapshot de iFiles (atómico)
                try:
                    snapshot = {
                        "version": 1,
                        "created": time.time(),
                        "fs": {"fingerprint": scan_fs_state},
                        "files": iFiles
                    }
                    atomic_write_json(content_config_file, snapshot)
                    logger.info("Updated file snapshot (%d entries)", nFi)
                except Exception as e:
                    logger.warning("Could not persist snapshot after rescan: %s", str(e))
                next_check_tm=time.time()+check_dirs #update next check time


         
# Keyboard and button handling
      #delta=time.time()-86400.0
      delta=0

# WHILE LOOP ends here       
 
    try:
      DISPLAY.loop_stop()
    except Exception as e:
      logger.error("this was going to fail if previous try failed!")
    if KEYBOARD:
      kbd.close()
    os.system(CMD_SCREEN_OFF) # turn screen off
    logger.info("Screen OFF")
    DISPLAY.destroy()
    save_geo_cache()
    logger.info("End of slideshow")
    # end of main function    


###next block parses command line arguments and invokes main function




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
        type=int,
        dest='dirchecktm',
        action='store',
        default=config.CHECK_DIR_TM,
        help='Interval between check directories'
        )
    parser.add_argument(
        '--weather-time',
        type=int,
        dest='weathertime',
        action='store',
        default=0,
        help='Time to show weather forecast in seconds'
        )
    parser.add_argument(
        '--logfile',
        action='store',
        dest='logfile',
        default=config.LOG_FILE,
        help='Log file to write log messages to'
        )
    parser.add_argument(
        '--debug',
        action='store_true',
        dest='debug',
        default=False,
        help='Enable debug mode'
        )

    args = parser.parse_args()
    

    main(startdir=args.path,
      config_file=args.config,
      interval=args.waittime,
      shuffle=args.shuffle,
      geonamesuser=args.geouser,
      check_dirs=args.dirchecktm,
      weathertime=args.weathertime,
      logfile=args.logfile,
      debug=args.debug
      )

# end of argument parsing
