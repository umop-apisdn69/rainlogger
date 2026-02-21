# Rainlogger

Raspberry Pi Zero W weather station daemon — records rainfall (tipping bucket),
temperature, and humidity (DHT22, DS18B20) to SQLite.

## Task tracking
Use 'bd' for task tracking.

## Structure
- `src/rain.py` — Main daemon (GPIO interrupt-driven rain gauge + periodic sensor reads)
- `scripts/ws.py` — Multi-day weather summary report
- `scripts/*.sql` — Daily detail queries

## Constraints
- Target: Raspberry Pi Zero W, Python 3.x
- Hardware-dependent (GPIO sensors) — cannot run or test locally
- Database: ~/rain/weather/weather.db (SQLite)
- No test suite
