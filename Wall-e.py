from machine import PWM, Pin
import time
import math
import random


neck = PWM(Pin(4), freq=50, duty_u16=0)
deg2serv = 65535/20 # Converts from .5 - 2.5 in a 0 - 180 deg range

front = int(1.5*deg2serv)
left = int(0.5*deg2serv)
right = int(2.5*deg2serv)

neck.duty_u16(front)

# initialize buttons
button_Decision = Pin(34, Pin.IN, Pin.PULL_UP)

# decision mode
def decisionMode():
    pick = random.randint(1, 2)  # 1 = left, 2 = right
    if pick == 1:
        print("Left")
        neck.duty_u16(left)
    else:
        print("Right")
        neck.duty_u16(right)
    time.sleep(2)       # hold the answer
    move_to(front)      # return to front
     
last_press = 0
pressed_flag = False
 
def decisionButton(pin):
    global pressed_flag
    global last_press
    last_press = True
 
 
# FALLING = fires when pin goes 1 -> 0 (active-low button).
# Change to Pin.IRQ_RISING if your button reads 1 when pressed.
button_Decision.irq(trigger=Pin.IRQ_FALLING, handler=decisionButton)
    
    
    
    
while True:
    if button_just_pressed():
        decision_mode()
    time.sleep_ms(10)








