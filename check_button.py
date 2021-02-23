#--coding: utf-8 --
#!/usr/bin/python3

from gpiozero import Button
from time import sleep





def hasbeenheld(btn) :
  global action
  btn.was_held=True
  action=True
  print("button ",btn.pin ,"was held not just pressed")

def hasbeenpressed(btn) :
  print("button ",btn.pin ,"was pressed not held")

def hasbeenreleased(btn):
  global action
  if not btn.was_held :
    hasbeenpressed(btn)
  btn.was_held = False
  action=False

Button.was_held=False
action=False 
back = Button(8,hold_time=10)
play = Button(9,hold_time=10)
back.was_held=False
play.was_held=False
back.when_held=hasbeenheld
play.when_held=hasbeenheld
back.when_released=hasbeenreleased
play.when_released=hasbeenreleased


while True :
  if back.was_held :
    print ("Action!! on back",action)
    
  if play.was_held :
    print("Action!! on play", action)
  
  sleep(1)