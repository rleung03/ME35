# Yeller (peripheral) - sends joystick as -100..100 (0 = center),
# ONLY when the stick moves, so if not moving the joystick, the car stops
# Plays a series of notes and flash LEDs when the car sees red
# Backup: press onboard button D34 to celebrate by hand

from BLE_CEEO import Yell
from machine import Pin, ADC, PWM       # >>> added PWM for the buzzer
import time
import json
import neopixel

NAME = "Hello"
buffer = b""

CHECK_EVERY_MS = 50     # read the joystick 20 times per second
CHANGE = 5              # only send if x or y moved more than this (out of -100..100)
DEADZONE = 10           # values within +-10 of center are sent as exactly 0

# Joystick limits measured (0-1023 scale)
X_LEFT  = 236           # stick fully left
X_RIGHT = 724           # stick fully right
Y_UP    = 220           # stick fully up   (raw value goes DOWN when pushed up)
Y_DOWN  = 650           # stick fully down
CLICK_RAW = 950         # raw X above this = stick pressed down (click), not a real push

# Joystick has two potentiometers inside, so it reads x-y positions
joy_x = ADC(Pin(32))                    # joystick X on Grove 6
joy_y = ADC(Pin(39))                    # joystick Y on Grove 6
joy_x.atten(ADC.ATTN_11DB)              # read the full 0-3.3V range
joy_y.atten(ADC.ATTN_11DB)

# >>> NEW: backup - onboard button D34 triggers the celebration by hand
btn34 = Pin(34, Pin.IN)

# Piezo buzzer makes sound via vibration
BUZZER_PIN = 23
buzzer = PWM(Pin(BUZZER_PIN))
buzzer.duty_u16(0)                      # start silent
color_r, color_g, color_b, color_w = 0, 0, 0, 0     # latest color reading from the car
new_color = False                       # True when a new reading has arrived

# Note frequencies in Hz (C4 = middle C)
NOTES = {
    "C4": 262, "D4": 294, "E4": 330, "F4": 349,
    "G4": 392, "A4": 440, "B4": 494, "C5": 523,
    "D5": 587, "E5": 659, "F5": 698, "G5": 784, "A5": 880, "C6": 1047,   # higher notes
    "REST": 0,                                                           # silence
}

np = neopixel.NeoPixel(Pin(15), 2)


def set_leds(color):
    np[0] = color
    np[1] = color
    np.write()


def play(note, duration):
    """Play one note for 'duration' seconds. "REST" = silence."""
    if note == "REST":
        buzzer.duty_u16(0)
    else:
        buzzer.freq(NOTES[note])
        buzzer.duty_u16(32768)
    time.sleep(duration)
    buzzer.duty_u16(0)
    time.sleep(0.05)                # tiny gap so repeated notes sound separate


# Each step: (note, seconds, LED color)
VICTORY_SONG = [
    ("C5", 0.12, (40, 0, 0)),      # red
    ("E5", 0.12, (40, 20, 0)),     # orange
    ("G5", 0.12, (40, 40, 0)),     # yellow
    ("C6", 0.30, (0, 40, 0)),      # green
    ("REST", 0.08, (0, 0, 0)),     # off (pause)
    ("G5", 0.12, (0, 0, 40)),      # blue
    ("C6", 0.50, (30, 0, 40)),     # purple
]


def celebrate():
    """Play the victory song with matching lights, then flash and turn off."""
    for note, duration, color in VICTORY_SONG:
        set_leds(color)            # change the lights first...
        play(note, duration)       # ...then play that note
    for _ in range(3):             # finish with 3 white flashes
        set_leds((40, 40, 40))
        time.sleep_ms(100)
        set_leds((0, 0, 0))
        time.sleep_ms(100)


def read_raw(adc):
    return adc.read_u16() // 64         # 0-65535 -> 0-1023


def read_center(adc):
    """Average 20 readings while the stick is untouched = its center value (0-1023)."""
    total = 0
    for _ in range(20):
        total += read_raw(adc)
        time.sleep_ms(10)
    return total // 20


def to_percent(v, center, low_end, high_end):          # value sent to listener in a scale of [-100,100]
    """
    Map a raw reading to -100..100, with 0 at center.
    low_end  -> -100, high_end -> +100.
    Each side is scaled separately, so a full push reaches 100 in BOTH directions
    even when the two sides of the joystick have different reach.
    """
    if v >= center:
        out = (v - center) / (high_end - center) * 100
    else:
        out = (v - center) / (center - low_end) * 100
    out = max(-100, min(100, out))                     # never beyond -100..100
    if abs(out) < DEADZONE:
        return 0                                       # resting wobble -> exactly 0
    return int(out)


def read_joystick():
    rx = read_raw(joy_x)
    ry = read_raw(joy_y)
    if rx >= CLICK_RAW:
        x = 0                                          # click: ignore, don't treat as full right
    else:
        x = to_percent(rx, cx, X_LEFT, X_RIGHT)        # left = -100, right = +100
    y = -to_percent(ry, cy, Y_UP, Y_DOWN)              # minus sign flips it: up = +100, down = -100
    return x, y


def is_red(r, g, b, w):
    if g == 0 or b == 0:
        return False
    return (r / g) > 1.15 and (r / b) > 2.0


def callback(data):
    # Pieces arrive in up to 20-byte chunks; a newline ends each message
    # Kept SHORT: only stores the color numbers - the main loop decides what to do
    global buffer, color_r, color_g, color_b, color_w, new_color   # >>> NEW: color_w added
    buffer += data
    while b"\n" in buffer:
        line, buffer = buffer.split(b"\n", 1)
        text = line.decode().strip()
        print("Received:", text)
        try:
            msg = json.loads(text)                           # text -> dictionary
            if "r" in msg:                                   # is it a color message?
                color_r = msg["r"]
                color_g = msg["g"]
                color_b = msg["b"]
                color_w = msg["w"]
                new_color = True                             # tell the main loop
                if is_red(color_r, color_g, color_b, color_w):
                    print("sees red")                        # every red reading
        except (ValueError, KeyError):                       # >>> NEW: KeyError added
            pass                                             # not JSON / missing key -> ignore it


# Measure the resting center before connecting (don't touch the joystick)
print("Calibrating joystick... don't touch it")
cx = read_center(joy_x)
cy = read_center(joy_y)
print("Center (raw):", cx, cy)

p = None
try:
    p = Yell(NAME, interval_us=30000, verbose=False)
    p.callback = callback

    print("Waiting for a listener...")
    if p.connect_up():
        print("Connected")
        last_x, last_y = None, None     # last values actually sent (None = send the first one)
        celebrated = False
        rest34 = btn34.value()          # >>> NEW: what D34 reads when NOT pressed
        was34 = False                   # >>> NEW: was D34 pressed last loop?

        while p.is_connected:
            x, y = read_joystick()      # now -100..100, 0 = center, up = +

            # Red tape seen by the car -> celebrate (once)
            if new_color:
                new_color = False
                if is_red(color_r, color_g, color_b, color_w) and not celebrated:
                    celebrated = True   # celebrate only once
                    print("red detected")
                    try:                                # >>> NEW: stop the car before the song
                        p.send('{"x":0,"y":0}\n')
                        last_x, last_y = 0, 0
                    except OSError:
                        pass
                    celebrate()

            # >>> NEW: backup - D34 pressed -> celebrate (in case the red tape was missed)
            pressed34 = btn34.value() != rest34
            if pressed34 and not was34:
                print("backup button: celebrate")
                try:
                    p.send('{"x":0,"y":0}\n')           # stop the car before the song
                    last_x, last_y = 0, 0
                except OSError:
                    pass
                celebrate()
            was34 = pressed34

            moved = (last_x is None
                     or abs(x - last_x) > CHANGE
                     or abs(y - last_y) > CHANGE
                     or (x == 0 and last_x != 0)       # always send the return to center
                     or (y == 0 and last_y != 0))

            if moved:
                payload = json.dumps({"x": x, "y": y}).replace(" ", "") + "\n"
                try:
                    p.send(payload)
                    last_x, last_y = x, y   # remember what was sent (only if it went through)
                    print("Sent:", x, y)
                except OSError:
                    print("BLE busy, will retry")
                    time.sleep_ms(50)

            time.sleep_ms(CHECK_EVERY_MS)
    print("Lost connection")
finally:
    buzzer.duty_u16(0)                  # make sure the buzzer is silent at the end
    set_leds((0, 0, 0))                 # >>> NEW: make sure the LEDs are off at the end
    if p:
        p.disconnect()
