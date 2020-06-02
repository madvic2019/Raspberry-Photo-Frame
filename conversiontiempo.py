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

parser.add_argument(
  '--check',
  dest="number",
  type=int,
  default=0,
  help='File number to check'
)

args=parser.parse_args()
numberfilename=args.path+".num"
print("Working with ",args.path," ",numberfilename)

try:
  with open(args.path,'r') as f:
    picturesnameslist=json.load(f)
  if(args.number != 0):
    print("File number ",args.number," is ",picturesnameslist[args.number])
  with open(numberfilename,'r') as g:
    data=json.load(g)
    print("Next Picture to be shown: ",picturesnameslist[data[1]]," number ",data[1])
    print("Last File Change: ",time.strftime("%d/%m %H:%M:%S", time.localtime(data[2])))
    print("Next Directory check: ",time.strftime("%d/%m %H:%M:%S",time.localtime(data[3])))

except Exception as e:
  print(e)