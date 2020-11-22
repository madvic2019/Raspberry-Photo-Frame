#--coding: utf-8 --
#!/usr/bin/python3

from gpiozero import Button
from time import sleep

buttons = {Button(9),Button(8),Button(4),Button(5),Button(6),Button(7)}


while True:
    for button in buttons :
        if button.is_pressed:
            print("Pressed")
        else:
            print("Released")
        sleep(1)
	
	