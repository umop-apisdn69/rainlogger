#!/usr/bin/env python3

################################################################################
# rain.py v1.0   Frank L. Sherwood 2026-02-13
#
################################################################################
# Copyright (C) 2026 Frank L. Sherwood
# All rights reserved.
# 
# This project is publicly viewable for reference only.
# No permission is granted to copy, modify, distribute, or use this code.
# 
################################################################################

################################################################################
# Code module for rain.service 
# 1) Creates an interrupt-driven background thread 
#    that triggers on signal from the rain sensor 
#    and writes the configured bucket amount in inch-equivalent 
#    to SQLite3 table datapoints in database WeatherData 
# 2) Runs a loop that records DHT22 temp & humidity 
#    and DS18B20 temp to the same database table 
#    every Increment minutes, on even multiples from the hour
# All records include datetimestamp to nearest second.
########################################
import RPi.GPIO as GPIO
import time
from datetime import datetime
import sqlite3
import Adafruit_DHT
import os
import glob
import threading
import logging

#######################################################################
# Pin roles by physical PIN, custom cable wire, and GPIO (BCM) number #
#######################################################################
#  Role        GPIO  Cable PIN | PIN  Cable GPIO   Role               #
#  --------    ----   ---  --  + --    ---  ----   ------------------ #
#  GND         GND     01  09  | 10     02  15     DS18b20 IN: 1-Wire #
#  DHT22 IN    17      03  11  | 12     04  18     Bucket IN          #
#  (BMP280?)   27      05  13  | 14     06  GND    GND                #
#              22      07  15  | 16     08  23                        #
#  3.3V        3.3V    09  17  | 18     10  24     (Reserve RELAY OUT)#
#######################################################################
# DHT22 needs 2 sec for stable reading
# GPIO pin numbers
DS18B20Pin = 10 # BOARD.10 = GPIO.15 - Redefined 1-Wire pin 
DHT22Pin   = 17 # BOARD.11 = GPIO.17 - Adafruit_DHT library requires the GPIO numbering 17
BucketPin  = 12 # BOARD.12 = GPIO.18

Tips = 0
Increment  = 10 # Number of minutes between timed data points; best 1, 5, 10, 30, 60

# Initialize the DHT22 sensor
DHT_SENSOR = Adafruit_DHT.DHT22

# DS18B20 setup
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

base_dir = '/sys/bus/w1/devices/'
device_folders = glob.glob(base_dir + '28*')
if device_folders:
    device_folder = device_folders[0]
    device_file = device_folder + '/w1_slave'
else:
    print("No DS18B20 sensors found. Exiting.")
    exit(1)  # Exit if no sensors found

def read_temp_raw():
    with open(device_file, 'r') as f:
        return f.readlines()

def read_ds18b20_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        temp_f = round(temp_c * 9.0 / 5.0 + 32.0, 2)
        return temp_f

def read_dht22():
    humidity, temperature_c = Adafruit_DHT.read_retry(DHT_SENSOR, DHT22Pin)
    if humidity is not None and temperature_c is not None:
        temperature_c = round(temperature_c, 2)
        humidity = round(humidity, 2)
        temperature_f = round(temperature_c * 9.0 / 5.0 + 32.0, 2)
        return temperature_f, humidity
    else:
        return None, None

# Rain bucket size (in decimal inches per tip)
BucketSize = 0.0136     # Calibrated 32 oz over 20 min slow pour -> 254 tips
# Database setup
db_path = os.path.expanduser("~/rain/weather/weather.db")
conn = sqlite3.connect(db_path, check_same_thread=False)
c = conn.cursor()
db_lock = threading.Lock()

# Create WeatherEvents table if not exists
c.execute('''
    CREATE TABLE IF NOT EXISTS WeatherEvents (
        c_mod TEXT,
        c_bucket REAL,
        c_thi_temp REAL,
        c_thi_hum REAL,
        c_temp REAL
    )
''')
conn.commit()

# Initialize GPIO
GPIO.setmode(GPIO.BOARD)
#GPIO.setup(BucketPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BucketPin, GPIO.IN)

# Set up logging
log_file = os.path.expanduser("~/rain/weather/rain6.log")
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    handlers=[logging.FileHandler(log_file),
                              logging.StreamHandler()])

def rain_interrupt(channel):
    global Tips
    # Record rain event
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    Tips += 1
    logging.info(f"Rain Tip {Tips} detected")
    with db_lock:
        c.execute('INSERT INTO WeatherEvents (c_mod, c_bucket) VALUES (?, ?)', (current_time, BucketSize))
        conn.commit()

# Set up rain sensor interrupt
def monitor_rain():
    GPIO.add_event_detect(BucketPin, GPIO.FALLING, callback=rain_interrupt, bouncetime=200)
    while True:
        time.sleep(1)  # Keep the thread alive

# Wait till clock is an even multiple of (interval) minutes
def wait_for_next_multiple_of_minutes(interval):
    if interval <= 0:
        raise ValueError("Interval must be a positive integer")
    
    now = datetime.now()
    start_minute = now.minute
    target_minute = ((start_minute // interval) + 1) * interval
    if target_minute >= 60:
        target_minute = target_minute % 60
    
    while True:
        current_time = datetime.now()
        current_minute = current_time.minute
        if (current_minute % interval == 0 and current_minute != start_minute) or current_minute == target_minute:
            break
        time.sleep(1)

# Create and start the rain sensor monitoring thread
rain_thread = threading.Thread(target=monitor_rain, daemon=True)
rain_thread.start()
logging.info("Rain sensor monitoring started in background. Press Ctrl-C to exit.")

try:
    while True:
        wait_for_next_multiple_of_minutes(Increment)
        ds18b20_temp = read_ds18b20_temp()
        dht22_temp, dht22_humidity = read_dht22()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if ds18b20_temp is not None and dht22_temp is not None and dht22_humidity is not None:
            with db_lock:
                c.execute('INSERT INTO WeatherEvents (c_mod, c_thi_temp, c_thi_hum, c_temp) VALUES (?, ?, ?, ?)',
                          (current_time, dht22_temp, dht22_humidity, ds18b20_temp))
                conn.commit()

except KeyboardInterrupt:
    logging.info("Exiting gracefully...")
finally:
    GPIO.cleanup()
    conn.close()
