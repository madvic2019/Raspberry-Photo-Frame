#!/usr/bin/env python
"""
A pygame program to show a slideshow of all images buried in a given directory.

Originally Released: 2007.10.31 (Happy halloween!)

"""
from __future__ import division
import argparse
import os
import stat
import sys
import time
import datetime
from PIL import Image, ExifTags, ImageFilter # these are needed for getting exif data from images
from PIL.ExifTags import GPSTAGS,TAGS
from geopy.geocoders import GeoNames


import pygame
from pygame.locals import QUIT, KEYDOWN, K_ESCAPE


#weather
import pyowm



file_list = []  # a list of all images being shown
title = "pgSlideShow | My Slideshow!"  # caption of the window...
waittime = 5   # default time to wait between images (in seconds)


def walktree(top, callback):
    """recursively descend the directory tree rooted at top, calling the
    callback function for each regular file. Taken from the module-stat
    example at: http://docs.python.org/lib/module-stat.html
    """
    for f in os.listdir(top):
        pathname = os.path.join(top, f)
        mode = os.stat(pathname)[stat.ST_MODE]
        if stat.S_ISDIR(mode):
            # It's a directory, recurse into it
            walktree(pathname, callback)
        elif stat.S_ISREG(mode):
            # It's a file, call the callback function
            callback(pathname)
        else:
            # Unknown file type, print a message
            print ('Skipping %s', pathname)


def addtolist(file, extensions=['.png', '.jpg', '.jpeg', '.gif', '.bmp']):
    """Add a file to a global list of image files."""
    global file_list  # ugh
    filename, ext = os.path.splitext(file)
    e = ext.lower()
    # Only add common image types to the list.
    if e in extensions:
        #print ('Adding to list: ', file)
        file_list.append(file)
    else:
        print ('Skipping: ', file, ' (NOT a supported image)')


def input(events):
    """A function to handle keyboard/mouse/device input events. """
    for event in events:  # Hit the ESC key to quit the slideshow.
        if (event.type == QUIT or
            (event.type == KEYDOWN and event.key == K_ESCAPE)):
            pygame.quit()


def timeSince(lastTime,interval):
    if (time.time() - lastTime)>=interval:
        return True
    else:
        return False
    

def get_geotagging(exif):
    if not exif:
        #return None
        raise ValueError("Get Geotag: No EXIF metadata found")

    geotagging = {}
    for (idx, tag) in TAGS.items():
        if tag == 'GPSInfo':
            if idx not in exif:
                print("No GeoTag")
                raise ValueError("No EXIF geotagging found")

            for (key, val) in GPSTAGS.items():
                if key in exif[idx]:
                    geotagging[val] = exif[idx][key]

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

def get_geo_name(coords) :
  geocoder=None
  if coords is not None:
    geoloc=GeoNames(username='madvic')
    print("Retrieving Location from Geonames")
    geocoder=geoloc.reverse(coords,10)
    print("Location Name received",geocoder)
  return geocoder
  
def upright(im,orientation) :
    print("Orientation = ", orientation)
    surface=im
    if orientation == 2:
        surface=pygame.transform.flip(im,True,False)
    if orientation == 3:
        surface=pygame.transform.rotate(im,180) # rotations are clockwise
    if orientation == 4:
        surface=pygame.transform.flip(im,False,True)
    if orientation == 5:
        surface=pygame.transform.rotate(pygame.transform.flip(im,True,False),270)
    if orientation == 6:
        surface=pygame.transform.rotate(im,270)
    if orientation == 7:
        surface=pygame.transform.rotate(pygame.transform.flip(im,True,False),90)
    if orientation == 8:
        surface=pygame.transform.rotate(im,-90)
    return surface



    
def main(startdir="."):
    global file_list, title, waittime
    # Initialize EXIF tags
    EXIF_DATID = None # this needs to be set before get_files() above can extract exif date info
    EXIF_ORIENTATION = None
    for k in ExifTags.TAGS:
      if ExifTags.TAGS[k] == 'DateTimeOriginal':
        EXIF_DATID = k
      if ExifTags.TAGS[k] == 'Orientation':
        EXIF_ORIENTATION = k
        
    lastSwitch=time.time()
    lastWeather=time.time()
    
    owm = pyowm.OWM('4cc9ae1d116c7e70c145252ab605f260')
    observation = owm.weather_at_place('Ottawa,CA')
    w = observation.get_weather()
    temperature=(w.get_temperature('celsius'))['temp']
    status=w.get_status()
    #print (w)

    pygame.init()

    # Test for image support
    if not pygame.image.get_extended():
        print ("Your Pygame isn't built with extended image support.")
        print ("It's likely this isn't going to work.")
        sys.exit(1)

    walktree(startdir, addtolist)  # this may take a while...
    if len(file_list) == 0:
        print ("Sorry. No images found. Exiting.")
        sys.exit(1)

    modes = pygame.display.list_modes()
    print(max(modes))
    pygame.display.set_mode( (1280, 1024))
    #pygame.display.set_mode( max(modes))

    screen = pygame.display.get_surface()
    screen_width, screen_height= screen.get_size()
    pygame.display.set_caption(title)
    #pygame.display.toggle_fullscreen()
    #pygame.display.set_mode(max(modes),pygame.FULLSCREEN)
    pygame.display.set_mode((1280,1024),pygame.FULLSCREEN)
    pygame.mouse.set_visible(0)
    
    #create font
    timeFont = pygame.font.Font("indulta/Indulta-SemiSerif-boldFFP.otf", 40)
    dateFont = pygame.font.Font("indulta/Indulta-SemiSerif-boldFFP.otf", 40)
    weatherFont = pygame.font.Font("indulta/Indulta-SemiSerif-boldFFP.otf", 40)
    InfoFont = pygame.font.Font("indulta/Indulta-SemiSerif-boldFFP.otf", 40)
    
    print (str(waittime) +"wait time")
    

    current = 0
    num_files = len(file_list)
    location=None
    datestruct=None
    orientation=1
    while(True):
        try:
            # process image only once per cycle
            if timeSince(lastSwitch,waittime):
                current = (current + 1) % num_files
                lastSwitch=time.time()
                screen.fill(0) #time to switch to new photo, clean screen
                #Collect date taken and Location Name for next photo
                exif_data=Image.open(file_list[current])._getexif()
                try:        
                    orientation = int(exif_data[EXIF_ORIENTATION])
                except:
                    orientation = 1
                try:
                    location=get_geo_name(get_coordinates(get_geotagging(exif_data)))
                except:
                    print("No GeoTag")
                    location=None
                try:
                    dt = time.mktime(time.strptime(exif_data[EXIF_DATID], '%Y:%m:%d %H:%M:%S'))
                    dates=time.localtime(dt)
                    datestruct=str(dates.tm_mday) + "/" + str(dates.tm_mon) + "/" + str(dates.tm_year)
                except:
                    print('No Date')
                    dt = None
                    datestruct=None
                #Process Image
                img = pygame.image.load(file_list[current])
                img = img.convert()
                tempX,tempY=img.get_size()
                ratio =tempX/tempY
                tempSize=(screen_width,int(screen_width/ratio))
                #print (str(img.get_size())+" to "+ str(tempSize) +"and ratio: "+str(ratio))
                # rescale the image to fit the current display
                img = pygame.transform.scale(img, tempSize)
                img = upright(img,orientation)
                screen.blit(img, (0, 0))
                
            
            #gets current weather
            if timeSince(lastWeather,30):
                observation = owm.weather_at_place('Alcala de Henares,ES')
                w = observation.get_weather()
                temperature=(w.get_temperature('celsius'))['temp']
                status=w.get_status()
                print( status)
                lastWeather=time.time()
                print ("updating weather")
            
            #gets the current time and displays it
            timeText=datetime.datetime.now().strftime("%I:%M%p")
            dateText=datetime.datetime.now().strftime("%B %d, %Y")
            weatherText=str(int(temperature))+"`C  "+status
            
            
            timeLabel = timeFont.render(timeText, 1, (255,255,255))
            dateLabel = dateFont.render(dateText, 1, (255,255,255))
            weatherLabel = weatherFont.render(weatherText, 1, (255,255,255))
            
            timeWidth, timeHeight= timeLabel.get_size()
            dateWidth, dateHeight= dateLabel.get_size()
            weatherWidth, weatherHeight= weatherLabel.get_size()
            
            if location is None or datestruct is None : #in absence of exif tags, show weather and date
              screen.blit(weatherLabel, (0, screen_height-weatherHeight))
              screen.blit(timeLabel, (screen_width-timeWidth, screen_height-timeHeight-dateHeight))
              screen.blit(dateLabel, (screen_width-dateWidth, screen_height-dateHeight))
            else :
                if location is not None : #We have GPS data, show it
                    LocationLabel = InfoFont.render(str(location), 1, (255,255,255))
                    LocWidth, LocHeight= LocationLabel.get_size()
                    screen.blit(LocationLabel, (0, 0))
                if datestruct is not None :
                    DateLabel=InfoFont.render(str(datestruct),1,(255,255,255))
                    DateWidth,DateHeight = DateLabel.get_size()
                    screen.blit(DateLabel,(screen_width-DateWidth,screen_height-DateHeight))
                            
            pygame.display.flip()

            input(pygame.event.get())
            time.sleep(1)
            #gets the Geolocation if existing
            
            
            
        except pygame.error as err:
            print ("Failed to display %s: %s", file_list[current], err)
            sys.exit(1)


              


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Recursively loads images '
        'from a directory, then displays them in a Slidshow.'
    )

    parser.add_argument(
        'path',
        metavar='ImagePath',
        type=str,
        default='.',
        nargs="?",
        help='Path to a directory that contains images'
    )
    parser.add_argument(
        '--waittime',
        type=int,
        dest='waittime',
        action='store',
        default=1,
        help='Amount of time to wait before showing the next image.'
    )
    parser.add_argument(
        '--title',
        type=str,
        dest='title',
        action='store',
        default="pgSlidShow | My Slideshow!",
        help='Set the title for the display window.'
    )
    args = parser.parse_args()
    #waittime = args.waittime
    
    title = args.title
    main(startdir=args.path)
