# Rain Logger (Raspberry Pi Zero W)

For primary components:
- Periodic temp/humidity logger (CLI/systemd timer) writing to a local SQLite DB
-- Includes a GPIO interrupt-driven callback function to log rain gauge events to the DB
- A python script to output daily statistics for a variable number of days
- A sql script to query and output all data from the current day ("today")
- A sql script to query and output all data from the prior day ("yesterday")

## Raspberry Pi setup (high level)
- Install dependencies (RPi.GPIO, Adafruit_DHT)
- Copy systemd unit/timer files from `systemd/` to `/etc/systemd/system/`
- Enable/start the units/timers

## Repo contents
- `src/` Python application code
- `scripts/` helper scripts (DB query/stats)
- `systemd/` systemd units/timers

## Notes
- SQLite database is not stored in this repo.
