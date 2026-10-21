from machine import PWM, Pin
import time
import math
import random
import neopixel

# define neck movements
neck = PWM(Pin(4), freq=50, duty_u16=0)
deg2serv = 65535/20 # Converts from .5 - 2.5 in a 0 - 180 deg range

FRONT = int(1.5*deg2serv)
LEFT = int(0.5*deg2serv)
RIGHT = int(2.5*deg2serv)

def look_left():
    neck.duty_u16(LEFT)

def look_right():
    neck.duty_u16(RIGHT)

def look_front():
    neck.duty_u16(FRONT)
    
def happy():
    look_left()
    time.sleep(0.5)
    look_right()
    time.sleep(0.5)
    look_front()
    
look_front()

# neopixel
lights = neopixel.NeoPixel(Pin(15),2)
def lights_on():
    lights[0] = (20,0,20) # set the color of 0th light to purple
    lights[1] = (0, 128, 20) # teal (some green + some blue)
    lights.write()
    
def lights_off():
    lights[0] = (0, 0, 0)
    lights[1] = (0, 0, 0)
    lights.write()
    

# initialize buttons
decision_pin = Pin(34, Pin.IN) # input only pin so don't need pull-up
study_pin = Pin(35, Pin.IN)

# DECISION MODE
def decision_mode():
    pick = random.randint(1, 2)  # 1 = left, 2 = right
    time.sleep(1)
    if pick == 1:
        print("Option 1")
        look_left()
    else:
        print("Option 2")
        look_right()
    time.sleep(2)       # hold the answer
    look_front()      # return to front
     
decision_flag = False
 
def on_decision_press(p):
    global decision_flag
    decision_flag = True
    
# STUDY MODE
STUDY_TIMER = 20 # seconds just for testing
BREAK_TIMER = 5


def study_mode():
    start = time.ticks_ms()
    last_happy = start
    happy_interval = random.randint(2,8)
    print("Study started: Focus for 30 minutes!")
    while time.ticks_diff(time.ticks_ms(), start) < STUDY_TIMER * 1000:
        if time.ticks_diff(time.ticks_ms(), last_happy) > happy_interval * 1000:
            happy()
            last_happy = time.ticks_ms()
            happy_interval = random.randint(2,8)
        time.sleep_ms(10)
    lights_on()
    time.sleep(2)
    print("10 minute break!")
    lights_off()
    time.sleep(BREAK_TIMER)
    print("Break is over!")
    
study_flag = False

def on_study_press(p):
    global study_flag
    study_flag = True
    
    
# set buttons to handler
decision_pin.irq(trigger=Pin.IRQ_FALLING, handler=on_decision_press) # falling = when pin goes from 1 -> 0
study_pin.irq(trigger=Pin.IRQ_FALLING, handler=on_study_press) # falling = when pin goes from 1 -> 0

    
while True:
    if decision_flag:
        decision_flag = False
        decision_mode()
        decision_flag = False
    if study_flag:
        study_flag = False
        study_mode()
        study_flag = False
    time.sleep_ms(10)
    


    









