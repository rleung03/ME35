# Listener (central)

from BLE_CEEO import Listen
import time
import json
from machine import Pin, PWM, I2C, SoftI2C
import veml6040
import neopixel



NAME = "Hello"     # must match the yeller's name
buffer = b""

# motor setup
left_pin = Pin(14, Pin.OUT)
right_pin = Pin(13, Pin.OUT)
left_pin.value(0)
right_pin.value(0)
left_pwm = PWM(Pin(27), freq=20000, duty_u16=0)
right_pwm = PWM(Pin(12), freq=20000, duty_u16=0)

# wait for button 34 before starting
start_btn = Pin(34, Pin.IN)
START_IDLE = start_btn.value()            # level when NOT pressed (don't hold it at power-up)
print("Waiting for button 34 to start...")
while start_btn.value() == START_IDLE:    # wait for a press
    time.sleep_ms(10)
while start_btn.value() != START_IDLE:    # wait for release
    time.sleep_ms(10)
print("Starting!")



# driving initiatlizations
FORWARD_SPEED = 0.8   # 1.0 = full speed, 0.5 = half speed
REVERSE_SPEED = 0.8   # raise or lower until reverse starts reliably

joy_x = 0
joy_y = 0

# set pins
buzzer = PWM(Pin(23), freq=1000, duty_u16=0)
i2c = SoftI2C(scl = Pin(22), sda = Pin(21))
neopixel = neopixel.NeoPixel(Pin(15),2)
    

# initialize buzzer
buzzer.duty_u16(0)
BEEP_FREQ = 1000
buzzer.freq(BEEP_FREQ)

# initialize color sensor
sensor = veml6040.VEML6040(i2c)
# sensor.trigger_measurement()
i2c.writeto_mem(0x10, 0x00, b'\x00\x00')   # VEML6040: 40 ms integration time, auto mode

# set colors
B = 60
WHITE  = (B, B, B)
RED    = (B, 0, 0)
ORANGE = (B, B // 4, 0)
OFF    = (0, 0, 0)

last_colors = None


# def drive(left, right):
#     
#     left = max(-1.0, min(1.0, left))
#     right = max(-1.0, min(1.0, right))
#     
#     # direction pin: 0 = forward, 1 = backward
#     left_pin.value(1 if left < 0 else 0)
#     right_pin.value(1 if right < 0 else 0)
#     
#     left_pwm.duty_u16(int(abs(left) * 65535))
#     right_pwm.duty_u16(int(abs(right) * 65535))
    
    
def drive(left, right):
    for pin, pwm, s in ((left_pin, left_pwm, left), (right_pin, right_pwm, right)):
        s = max(-1.0, min(1.0, s))
        duty = int(abs(s) * 65535)
        pin.value(1 if s < 0 else 0)
        # reverse: PWM is inverted on this kind of driver
        pwm.duty_u16(65535 - duty if s < 0 else duty)

def stop():
    left_pwm.duty_u16(0)
    right_pwm.duty_u16(0)
    left_pin.value(0)
    right_pin.value(0)

def lights(x,y):
    global last_colors
    blink = (time.ticks_ms() // 300) % 2 == 0
    
    if y > 0:
        left = right = WHITE # driving forward
        
    elif y < 0:  # reversing: alternate red/white
        left, right = (RED, WHITE) if blink else (WHITE, RED)
    
    else:
        left = right = RED              # stopped / brake lights
        
    # turn signals: the side you're turning toward flashes orange
    if x < -30:
        left = ORANGE if blink else OFF
    elif x > 30:
        right = ORANGE if blink else OFF

    colors = (left, right)
    if colors != last_colors:           # only write when something changed
        neopixel[0], neopixel[1] = left, right
        neopixel.write()
        last_colors = colors


# BLE
def callback(data):
    # Pieces arrive in up to 20-byte chunks; a newline ends each message
    global buffer, joy_x, joy_y
    buffer += data
    while b"\n" in buffer:
        line, buffer = buffer.split(b"\n", 1)
        print("Received:", json.loads(line.decode()))
        msg = json.loads(line.decode())
        joy_x = int(msg["x"])
        joy_y = int(msg["y"])


p = None
try:
    p = Listen(NAME, verbose=False)
    p.callback = callback

    print("Looking for", NAME, "...")
    if p.connect_up():
        print("Connected")
        last_color_send = time.ticks_ms()
        
        while p.is_connected:
#             r, g, b, w = sensor.read_rgbw()
#             print(sensor.read_rgbw())
        
            # send color about twice a second

            
            if time.ticks_diff(time.ticks_ms(), last_color_send) > 500:
                r, g, b, w = sensor.read_rgbw()
#                 sensor.trigger_measurement()
                p.send("{},{},{}\n".format(r, g, b))
                last_color_send = time.ticks_ms()
                
                
                payload = json.dumps({"r": r, "g": g, "b": b, "w": w}).replace(" ", "") + "\n"
                
                for start in range(0, len(payload), 20):
                    p.send(payload[start:start + 20])
                    time.sleep_ms(20)
            
            
            x, y = joy_x, joy_y

#             throttle = y / 100      # -1..1
#             turn = x / 100          # -1..1

            limit = REVERSE_SPEED if y < 0 else FORWARD_SPEED
            throttle = y / 100 * limit
            turn = x / 100 * FORWARD_SPEED

            left = throttle + turn
            right = throttle - turn

            if x == 0 and y == 0:
                stop()
                
            else:
                drive(left, right)
                
            # lights
            lights(x, y)
            
            time.sleep_ms(20)
            
    print("Lost connection")

finally:
    stop()
    buzzer.duty_u16(0)
    neopixel[0], neopixel[1] = OFF, OFF
    neopixel.write()
    if p:
        p.disconnect()
    
    
    

