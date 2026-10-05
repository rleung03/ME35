from machine import PWM, Pin, SoftI2C
import time
import math

# init servos
bins = PWM(Pin(18), freq=50, duty_u16=0) # Bin servo - Pin 18
pusher= PWM(Pin(4), freq=50, duty_u16=0) # Pusher servo - Pin 4
deg2serv = 65535/20 # Converts from .5 - 2.5 in a 0 - 180 deg range

bins.duty_u16(int(0.5*deg2serv))
pusher.duty_u16(int(2.5*deg2serv))

# init buttons
button_Play = Pin(34, Pin.IN, Pin.PULL_UP)
button_Train = Pin(35, Pin.IN, Pin.PULL_UP)
print("35 to Train, 34 to Sort")
print("Train by scanning RED 5 times")

# Color sensor wired to pin 21 and 22
i2c = SoftI2C(scl = Pin(22), sda = Pin(21)) 

DEBOUNCE_MS = 200
last_press = 0

pressed_flag = False
STATE_PLAY = False
STATE_TRAIN = True

def playButton(p):
    global STATE_PLAY
    global STATE_TRAIN
    STATE_PLAY = True
    STATE_TRAIN = False


def trainButton(p):
    global pressed_flag
    global STATE_TRAIN
    STATE_TRAIN = True
    pressed_flag = True

# set buttons to their handlers 
button_Train.irq(trigger=Pin.IRQ_RISING, handler=trainButton)
button_Play.irq(trigger=Pin.IRQ_RISING, handler=playButton)

# init color sensor
import veml6040
sensor = veml6040.VEML6040(i2c)

sensor.trigger_measurement()
   
# KNN algorithm 
def k_nearest_neighbor(x,y,z, k =2):
    distances = []
    for index, d in enumerate(data):
        dist = math.sqrt((x-d[0])**2+(y-d[1])**2+(z-d[2])**2)
        distances.append([dist,d[3]])
    
    distances.sort()
    distances = distances[:k] #get k distances
    classes = []
    for dist in distances:
        classes.append(dist[1])
    print("k classes", classes)
    most_number_of_closest_classes = max(set(classes), key = classes.count)
    
    return most_number_of_closest_classes
       
data = []
color = ""
index = 0

while True:
    red, green, blue, white = sensor.read_rgbw()
    if(STATE_TRAIN and pressed_flag): # train button!
        index = index+1
        
        if index <= 5: # first five
            color = "red"
        elif index >5 and index<=10: # 5-10
            color = "green"
        elif index >10 and index <= 15:
            color = "blue"
        else:
            color = "no clue" # the rest are any color that are not our expected red green or blue

        data.append((red, green, blue, color))
        print(data[-1], index) # print out the last recorded rgb values and stored color
        
        # Let the user know what to scan next
        if index == 5:
            print("Scan GREEN 5 times")
        elif index == 10:
            print("Scan BLUE 5 times")
        elif index == 15:
            print("Scan other colors however much you want")
            
        pressed_flag = False
           
    if(STATE_PLAY): # Check color button!
        what_class = k_nearest_neighbor(red, green, blue,3)
        # info for debugging
        print((red, green, blue))
        print(what_class)
        if what_class == "red":
            bins.duty_u16(int(0.5*deg2serv)) # first bin
        elif what_class == "green":
            bins.duty_u16(int(1*deg2serv)) # second bin
        elif what_class == "blue":
            bins.duty_u16(int(1.5*deg2serv)) # third
        else:
            bins.duty_u16(int(2*deg2serv)) # fourth
        
        time.sleep(1)
        
        # push lego
        pusher.duty_u16(int(0.5*deg2serv))
        time.sleep(0.5) # wait for motor to move
        pusher.duty_u16(int(2.5*deg2serv)) # return pos
        
        STATE_PLAY = False
    time.sleep(0.4)
