#--coding: utf-8 --
#!/usr/bin/python

import argparse
import time 
import json
import FrameConfig as config


  
parser = argparse.ArgumentParser(
        description='Converts to readablie time information in Picture Frame config file '
        )
        
parser.add_argument(
        'path',
        metavar='ImagePath',
        type=str,
        default=config.DEFAULT_CONFIG_FILE,
        nargs="?",
        help='Configuration file'
        )
args=parser.parse_args()


try:
  with open(args.path,'r') as f:
    data=json.load(f)
    print("Last File Change: ",time.strftime("%d de %m %H:%M:%S", time.localtime(data[2])))
    print("Next Directory check: ",time.strftime("%d de %m %H:%M:%S",time.localtime(data[3])))

except Exception as e:
  print(e)