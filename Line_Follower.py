# line_follow.py -- MicroPython, ESP32. Needs veml6040.py and knn.json on the board.
# CENTER = VEML6040 on I2C bus 0 (SDA 21, SCL 22), on the line.
# SIDE   = VEML6040 on SoftI2C (SDA 17, SCL 16), to the RIGHT of center,
#          over floor when on track.
# Line = ANY non-floor color from knn.json. NeoPixels show the color under
# the center sensor. Ctrl+C stops it.
from machine import Pin, PWM, I2C, SoftI2C
from neopixel import NeoPixel
import time, json, math
import veml6040

# ---------------- settings ----------------
BASE = 0.3
KP = 0.25
DEADBAND = 0.10
LOST_TIMEOUT = 2.0
FLOOR_LABEL = "floor"
THIN = 3
INTEGRATION = veml6040.IT_40MS   # IT_80MS matches training; 40 ms is faster

NEOPIXEL_PIN = 15    # change to the pin your strip's data wire is on
NUM_PIXELS = 2       # change to your pixel count
LIGHT_COLORS = {     # label -> (R, G, B); keep values low to limit current
    "floor": (4, 4, 4),
    "black": (40, 40, 40),
    "blue": (0, 0, 60),
    "green": (0, 60, 0),
    "red": (60, 0, 0),
}
OTHER_COLOR = (40, 0, 40)   # any label not listed above
# ------------------------------------------

left_pwm = PWM(Pin(27), freq=1000)
left_pin = Pin(14, Pin.OUT)
right_pwm = PWM(Pin(12), freq=1000)
right_pin = Pin(13, Pin.OUT)

pixels = NeoPixel(Pin(NEOPIXEL_PIN), NUM_PIXELS)
buzzer = PWM(Pin(23))
buzzer.duty_u16(0)


def set_light(color):
    pixels.fill(color)
    pixels.write()


def drive(left, right):
    left = max(0.0, min(1.0, left))
    right = max(0.0, min(1.0, right))
    left_pin.value(0)
    right_pin.value(0)
    left_pwm.duty_u16(int(left * 65535))
    right_pwm.duty_u16(int(right * 65535))


def stop():
    left_pwm.duty_u16(0)
    right_pwm.duty_u16(0)
    left_pin.value(0)
    right_pin.value(0)


floor_pts = []
line_pts = []
seen = {}
with open("knn.json") as f:
    for x, label in json.load(f):
        k = seen.get(label, 0)
        seen[label] = k + 1
        if k % THIN:
            continue
        if label == FLOOR_LABEL:
            floor_pts.append((x[0], x[1], x[2]))
        else:
            line_pts.append((x[0], x[1], x[2], label))
print("floor pts:", len(floor_pts), " tape pts:", len(line_pts))


def tape_score(sensor):
    """0 = floor, 1 = tape of any trained color. Returns (score, nearest_label)."""
    r, g, b, w = sensor.read_rgbw()
    if w == 0:
        return 1.0, "dark"
    x, y, z = r / w, g / w, b / w
    df = min((x - p[0]) ** 2 + (y - p[1]) ** 2 + (z - p[2]) ** 2 for p in floor_pts)
    dl, label = 1e9, "?"
    for p in line_pts:
        d = (x - p[0]) ** 2 + (y - p[1]) ** 2 + (z - p[2]) ** 2
        if d < dl:
            dl, label = d, p[3]
    df, dl = math.sqrt(df), math.sqrt(dl)
    score = df / (df + dl + 1e-6)
    return score, (FLOOR_LABEL if score < 0.5 else label)


def clamp01(v):
    return max(0.0, min(1.0, v))

# different color manuevers
def blue_tape(): # spin
    right_pin.value(0)
    left_pwm.duty_u16(0)
    right_pwm.duty_u16(int(0.7*65535))
    time.sleep(5)
    stop()
    
def greed_light():
    pixels[0] = (0,255,0)  
    pixels[1] = (0, 255, 0) 
    pixels.write()
    
def light_off():
    pixels[0] = (0, 0, 0)
    pixels[1] = (0, 0, 0)
    pixels.write()
    
def green_tape(): # flash green
    for _ in range(5):
        green_light()
        time.sleep(0.25)
        light_off()
        time.sleep(0.25)


def red_tape(): # play a scale
    C4, D4, E4, F4, G4, A4, B4, C5 = 262, 294, 330, 349, 392, 440, 494, 523
    song = [(C4, 250), (D4, 250), (E4, 250), (F4, 250),
            (G4, 250), (A4, 250), (B4, 250), (C5, 500),
            (B4, 250), (A4, 250), (G4, 250), (F4, 250),
            (E4, 250), (D4, 250), (C4, 500)]
    for freq, ms in song:
        buzzer.freq(freq)
        buzzer.duty_u16(32768)
        time.sleep_ms(ms)
        buzzer.duty_u16(0)
        time.sleep_ms(30)
    

i2c_center = I2C(0, sda=Pin(21), scl=Pin(22), freq=400000)
i2c_side = SoftI2C(sda=Pin(17), scl=Pin(16), freq=400000)
print("center bus:", i2c_center.scan(), " side bus:", i2c_side.scan())  # both [16]

center = veml6040.VEML6040(i2c_center)
side = veml6040.VEML6040(i2c_side)
for s in (center, side):
    s.set_integration_time(INTEGRATION)

try:
    stop()
    set_light((40, 30, 0))   # amber while waiting to start
    print("Put the car on the line: center sensor on tape, side sensor on floor.")
    print("Starting in 5 s")
    time.sleep(5)

    # ---- startup check + baseline ----
    N = 10
    cs = ss = 0.0
    for _ in range(N):
        a, c_lab = tape_score(center)
        b, s_lab = tape_score(side)
        cs += a
        ss += b
        time.sleep_ms(60)
    c1, s0 = cs / N, ss / N
    print("START CHECK: center score %.2f (%s), side score %.2f (%s)" % (c1, c_lab, s0, s_lab))
    if c1 < 0.5 and s0 > 0.5:
        print("Center looks like FLOOR and side looks like TAPE.")
        print("The two sensors are probably swapped. Swap the I2C bus lines in the code.")
        raise SystemExit
    if c1 < 0.5:
        print("The center sensor doesn't see tape. Check its position and the training data.")
        raise SystemExit
    if s0 > 0.5:
        print("The side sensor sees a tape-like color on the floor. Check its position/height,")
        print("or retrain with the sensor mounted on the car.")
        raise SystemExit
    print("GO")

    lost_since = None
    shown = None        # label currently shown on the pixels
    pending, pending_n = None, 0
    n = 0
    while True:
        c_raw, c_label = tape_score(center)
        s_raw, s_label = tape_score(side)

        # light the pixels for the center sensor's color (2 reads in a row to avoid flicker)
        if c_label == pending:
            pending_n += 1
        else:
            pending, pending_n = c_label, 1
        if pending_n >= 2 and pending != shown:
            shown = pending
            set_light(LIGHT_COLORS.get(shown, OTHER_COLOR))
        
        # do different things at blue, green, red tape
        if shown == "blue":
            stop()
            blue_tape()    
            continue
        
        if shown == "green":
            stop()
            green_tape()    
            continue
        
        if shown == "red":
            stop()
            red_tape()    
            continue
        
        # normalize against the startup baseline
        c = clamp01(c_raw / max(c1, 0.2))
        s = clamp01((s_raw - s0) / max(1.0 - s0, 0.2))

        # pos > 0: tape is to the RIGHT -> steer right
        # pos < 0: center is losing the tape (drifted left) -> steer left
        pos = s if s > DEADBAND else -(1.0 - c)

        if c < 0.1 and s < 0.1:
            if lost_since is None:
                lost_since = time.ticks_ms()
            elif time.ticks_diff(time.ticks_ms(), lost_since) > LOST_TIMEOUT * 1000:
                print("Line lost, stopping")
                break
        else:
            lost_since = None

        drive(BASE + KP * pos, BASE - KP * pos)

        n += 1
        if n % 5 == 0:
            print("c=%.2f(%s) s=%.2f(%s) pos=%+.2f" % (c, c_label, s, s_label, pos))
        time.sleep_ms(10)

finally:
    stop()
    set_light((0, 0, 0))
