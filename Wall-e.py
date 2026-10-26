from machine import PWM, Pin
import time
import math
import random
import neopixel
from machine import ADC

import urequests
import network
import ubinascii
import walle_secrets   # SSID, PASSWORD, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN

# establish wifi connection
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(walle_secrets.SSID, walle_secrets.PASSWORD)
        while not wlan.isconnected():
            time.sleep(0.5)
    print("Connected! IP address:", wlan.ifconfig()[0])
    return wlan

connect_wifi()

# SPOTIFY
TOKEN_URL = "https://accounts.spotify.com/api/token"
PLAY_URL = "https://api.spotify.com/v1/me/player/play"
PLAYLIST_URI = "spotify:playlist:1rA6M7mWmRNV2L2ZlcUzmu"   # the playlist to play
DEVICES_URL = "https://api.spotify.com/v1/me/player/devices"
DEVICE_NAME = "Rachel\u2019s MacBook Air"   # name your computer shows in Spotify's device list
PAUSE_URL = "https://api.spotify.com/v1/me/player/pause"
NEXT_URL = "https://api.spotify.com/v1/me/player/next"
current_device_id = None   # filled in when the music starts

# Basic auth for the token request: base64("client_id:client_secret")
basic = ubinascii.b2a_base64("{}:{}".format(walle_secrets.CLIENT_ID, walle_secrets.CLIENT_SECRET)).decode().strip()

access_token = None   # short-lived, so we get a fresh one each time we need it

def get_token():
    # trade the long-lived refresh token for a new access token
    global access_token
    headers = {'Authorization': 'Basic ' + basic,
               'Content-Type': 'application/x-www-form-urlencoded'}
    body = "grant_type=refresh_token&refresh_token=" + walle_secrets.REFRESH_TOKEN
    try:
        r = urequests.post(TOKEN_URL, headers=headers, data=body)
    except OSError as e:
        print("Token request failed:", e)
        return False
    try:
        if r.status_code != 200:
            print("Token status", r.status_code, r.text[:200])
            return False
        access_token = r.json()["access_token"]
        return True
    finally:
        r.close()

def get_device_id():
    # look up the id of the device named DEVICE_NAME
    headers = {'Authorization': 'Bearer ' + access_token}
    try:
        r = urequests.get(DEVICES_URL, headers=headers)
    except OSError as e:
        print("Device request failed:", e)
        return None
    try:
        if r.status_code != 200:
            print("Devices status", r.status_code, r.text[:200])
            return None
        names = []
        for d in r.json()["devices"]:
            names.append(d["name"])
            if d["name"] == DEVICE_NAME:
                return d["id"]
        print("Device not found. Spotify sees:", names)
        return None
    finally:
        r.close()

def start_music():
    # tell Spotify to start the playlist on the computer
    global current_device_id
    if not get_token():
        return
    device_id = get_device_id()
    if device_id is None:
        return
    current_device_id = device_id   # remember it for pause and skip
    url = PLAY_URL + "?device_id=" + device_id
    headers = {'Authorization': 'Bearer ' + access_token,
               'Content-Type': 'application/json'}
    body = '{"context_uri": "' + PLAYLIST_URI + '"}'
    try:
        r = urequests.put(url, headers=headers, data=body)
    except OSError as e:
        print("Play request failed:", e)
        return
    try:
        if r.status_code in (200, 202, 204):
            print("Music started")
        elif r.status_code == 404:
            print("No active device: open Spotify on your phone or computer first")
        elif r.status_code == 403:
            print("Not allowed: needs Premium and the playback permission", r.text[:200])
        else:
            print("Status", r.status_code, r.text[:200])
    finally:
        r.close()


def player_command(method, url):
    # send a pause or skip command to Spotify
    headers = {'Authorization': 'Bearer ' + access_token,
               'Content-Length': '0'}   # Spotify wants this on requests with no body
    try:
        if method == "PUT":
            r = urequests.put(url, headers=headers)
        else:
            r = urequests.post(url, headers=headers)
    except OSError as e:
        print("Command failed:", e)
        return
    try:
        if r.status_code not in (200, 202, 204):
            print("Status", r.status_code, r.text[:200])
    finally:
        r.close()

def pause_musi