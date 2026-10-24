from machine import PWM, Pin
import time
import math
import random
import neopixel
from machine import ADC

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
    neck.duty_u16(int(deg2serv))
    time.sleep(1)
    neck.duty_u16(int(2*deg2serv))
    time.sleep(1)
    look_front()
    
def shake():
    for _ in range(3):
        neck.duty_u16(int(deg2serv))
        time.sleep_ms(200)
        neck.duty_u16(int(2*deg2serv))
        time.sleep_ms(200)
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
    
def red_light():
    lights[0] = (255,0,0)
    lights[1] = (255,0,0)
    lights.write()

lights_off()
    
# joystick
joy_x = ADC(Pin(32))
joy_y = ADC(Pin(39))

joy_x.atten(ADC.ATTN_11DB)   # lets it read the full 0-3.3V range
joy_y.atten(ADC.ATTN_11DB)

    

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
STUDY_TIMER = 10 # seconds just for testing
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
    time.sleep(BREAK_TIMER)
    lights_off()
    print("Break is over!")
    
study_flag = False

def on_study_press(p):
    global study_flag
    study_flag = True


# PLAY MODE
def play_mode():
    game = [random.randint(0, 1) for _ in range(5)]
#     print(game) # answer
    sleep(1)
    for i in game:
        if i == 0:
            look_left()
            time.sleep(0.5)

        else:
            look_right()
            time.sleep(0.5)

        look_front()
        time.sleep(0.5)
        
    time.sleep(0.5)   # short pause so the player can get ready
    player = []

    for i in range(5):
        # wait for a push left or right
        while True:
            joy_dir = joy_x.read_u16()
            if joy_dir < 30000:
                player.append(0)
                break
            if joy_dir > 40000:
                player.append(1)
                break
            time.sleep_ms(10)

        # wait for the stick to return to center (keep going if not in center)
        while not (30000 <= joy_x.read_u16() <= 40000):
            time.sleep_ms(10)
            
        print(player)
    
    if game == player:
        print('Correct!')
        lights_on()
        
        
    else:
        print('Not Quite!')
        red_light()
        shake()
    
    
# set buttons to handler
decision_pin.irq(trigger=Pin.IRQ_FALLING, handler=on_decision_press) # falling = when pin goes from 1 -> 0
study_pin.irq(trigger=Pin.IRQ_FALLING, handler=on_study_press) # falling = when pin goes from 1 -> 0
    
while True:
#     if decision_flag:
#         decision_flag = False
#         decision_mode()
#         decision_flag = False
#     if study_flag:
#         study_flag = False
#         study_mode()
#         study_flag = False

    joy_dir = joy_x.read_u16()
    joy_press = joy_y.read_u16()
    if joy_press == 65535:
        play_mode()
        
    if joy_dir < 30000:
        decision_mode()
        
    if 60000 > joy_dir > 40000:
        study_mode()
    
    time.sleep_ms(10)
    


    









