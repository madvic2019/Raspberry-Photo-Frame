#--coding: utf-8 --
#!/usr/bin/python3

from gpiozero import Button
from time import sleep





def hasbeenheld(btn) :
  btn.was_held=True
  action=True
  print("button ",btn.pin ,"was held not just pressed")

def hasbeenpressed(btn) :
  print("button ",btn.pin ,"was pressed not held")

def hasbeenreleased(btn):
  if not btn.was_held :
    hasbeenpressed(btn)
  btn.was_held = False
  action=False

Button.was_held=False
action=False 
back = Button(8)
play = Button(9)
back.was_held=False
play.was_held=False
back.when_held=hasbeenheld
play.when_held=hasbeenheld
back.when_released=hasbeenreleased
play.when_released=hasbeenreleased


while True :
  if action :
    print ("Action!!")
    sleep(1)
  
  