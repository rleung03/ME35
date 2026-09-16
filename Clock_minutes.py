from machine import PWM, Pin
import time
servo = PWM(Pin(4), freq=50, duty_u16=0)


#Using duty_ns
# print("180 Degrees")
# servo.duty_ns(2500*1000)
# time.sleep(1)
# 
print("minute hand at 12")
servo.duty_ns(2500*1000)
time.sleep(0.5)

angle = 0
for minute in range(31):
    pulse = 2500 - (((2 * angle) / 180) * 1000)
    servo.duty_ns(int(pulse * 1000))
    print("Minute:", minute)
    time.sleep(0.5)
    angle = angle + 6

angle = 0
for minute in range(31,61):
    pulse = 500 + (((2 * angle) / 180) * 1000)
    servo.duty_ns(int(pulse * 1000))
    print("Minute:", minute)
    time.sleep(0.5)
    angle = angle + 6

servo.duty_ns(2500*1000)
time.sleep(0.5)
    
#     
#
# servo.duty_ns(2500*1000)
# time.sleep(1)


