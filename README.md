# Rain Logger (Raspberry Pi Zero W)

A weather monitoring daemon for Raspberry Pi that continuously records rainfall, temperature, and humidity to a local SQLite database.

## How it works

- **Rain gauge monitoring** -- A background thread uses GPIO interrupt-driven callbacks to record bucket-tip events from the rain gauge sensor (debounced at 200ms). Each tip logs a calibrated rainfall amount (0.0136") to the database.
- **Periodic sensor readings** -- The main loop samples the DHT22 (temperature + humidity) and DS18B20 (temperature) sensors every 10 minutes, aligned to even multiples from the hour.
- **Reporting scripts** -- SQL and Python scripts query the database for daily detail and multi-day summary statistics.

## Hardware

### Sensors
| Sensor | Measures | Interface |
|--------|----------|-----------|
| DHT22 | Temperature (F) + Humidity (%) | GPIO 17 (BOARD pin 11) |
| DS18B20 | Temperature (F) | 1-Wire via GPIO 15 (BOARD pin 10) |
| Rain gauge (tipping bucket) | Rainfall (inches) | GPIO 18 (BOARD pin 12) |

### Pin reference
```
 Role        GPIO  Cable PIN | PIN  Cable GPIO   Role
 --------    ----   ---  --  + --    ---  ----   ------------------
 GND         GND     01  09  | 10     02  15     DS18B20 IN: 1-Wire
 DHT22 IN    17      03  11  | 12     04  18     Bucket IN
 (BMP280?)   27      05  13  | 14     06  GND    GND
              22      07  15  | 16     08  23
 3.3V        3.3V    09  17  | 18     10  24     (Reserve RELAY OUT)
```

### 1-Wire setup for DS18B20
The daemon loads the required kernel modules at startup (`w1-gpio`, `w1-therm`). To have them load automatically on boot, add to `/boot/config.txt`:
```
dtoverlay=w1-gpio
```

## Repo contents
- `src/rain.py` -- Main daemon
- `scripts/ws.py` -- Multi-day weather summary (table-formatted output)
- `scripts/raintoday.sql` -- Detail query for the current calendar day
- `scripts/rainyesterday.sql` -- Detail query for the prior calendar day
- `systemd/` -- systemd service and timer units

## Setup

### 1. Install dependencies
```bash
pip install RPi.GPIO Adafruit_DHT prettytable
```
(Standard library modules like `sqlite3` and `threading` are not listed in `requirements.txt` but are included there for documentation purposes.)

### 2. Install the systemd units
```bash
sudo cp systemd/rain.service systemd/rain.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable rain.timer
sudo systemctl start rain.timer
```
The timer starts the service 1 minute after boot.

### 3. Verify
```bash
sudo systemctl status rain.service
```

## Configuration

These values are set as constants near the top of `src/rain.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `Increment` | `10` | Minutes between temp/humidity readings (1, 5, 10, 30, or 60) |
| `BucketSize` | `0.0136` | Rainfall per bucket tip in inches (calibrated) |
| `db_path` | `~/rain/weather/weather.db` | SQLite database location |
| `log_file` | `~/rain/weather/rain6.log` | Log file location |

## Database

The SQLite database is created automatically on first run and is not stored in this repo.

### Schema
```sql
CREATE TABLE WeatherEvents (
    c_mod      TEXT,    -- Timestamp (YYYY-MM-DD HH:MM:SS)
    c_bucket   REAL,    -- Rainfall amount per tip (inches), NULL for temp readings
    c_thi_temp REAL,    -- DHT22 temperature (F), NULL for rain events
    c_thi_hum  REAL,    -- DHT22 humidity (%), NULL for rain events
    c_temp     REAL     -- DS18B20 temperature (F), NULL for rain events
);
```

Rain events and temperature readings are stored as separate rows -- rain rows have only `c_mod` and `c_bucket` populated; temperature rows have only `c_mod`, `c_thi_temp`, `c_thi_hum`, and `c_temp` populated.

## Usage

### Weather summary (multi-day)
```bash
python3 scripts/ws.py 2026-02-01 2026-02-16
```
Outputs a color-formatted table with daily min/max/avg temperature and humidity, plus rainfall totals. The end date is exclusive.

### Today's detail
```bash
sqlite3 -header -column ~/rain/weather/weather.db < scripts/raintoday.sql
```

### Yesterday's detail
```bash
sqlite3 -header -column ~/rain/weather/weather.db < scripts/rainyesterday.sql
```

## License

All rights reserved. This project is publicly viewable for reference only. See [LICENSE](LICENSE) for details.
