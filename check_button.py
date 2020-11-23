#--coding: utf-8 --
#!/usr/bin/python3

from gpizero import ButtonBoard
from time import sleep

buttons = ButtonBoard(uno=9,dos=8,tres=4,cuatro=5,cinco=6,seis=7) 

while True :
  
  if buttons.uno.is_active :
    print("Boton uno !!")
  if buttons.dos.is_active :
    print("Boton dos !!")
  if button.tres.is_active :
    print("Boton tres !!")
  if buttons.cuatro.is_active :
    print("Boton cuatro !!")
  if buttons.cinco.is_active :
    print("Boton cinco !!")
  if button.seis.is_active :
    print("Boton seis !!")
    
