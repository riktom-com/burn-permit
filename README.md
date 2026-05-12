# Burn Permit Checker 🔥

Georgia burn permit conditions checker — **[burn.riktom.com](https://burn.riktom.com)**

Tells you whether open burning is currently permitted in your Georgia county by checking three live data sources simultaneously.

## Features
- 🔍 Look up by county name or ZIP code
- 📅 Check today's conditions or historical dates
- 🚫 **GFC burn ban detection** — live from the Georgia Forestry Commission firesponse system
- 🌩️ NWS Red Flag Warnings and Fire Weather Watches
- 🌲 GFC daily fire danger class (1 Low → 5 Extreme)
- Color-coded result: red ban, orange caution, green favorable

## Data Sources
- [GFC firesponse](https://georgiafc.firesponse.com/public/) — county burn bans
- [National Weather Service](https://api.weather.gov) — fire weather alerts
- [Georgia Forestry Commission](https://gatrees.org) — fire danger ratings

## Stack
- Python 3.12 + FastAPI backend
- Vanilla HTML/CSS/JS frontend
- SQLite for GFC fire danger history

## Legal Note
A burn permit is required by Georgia law for all outdoor burning. Permits are free — call **1-800-GA-TREES** or visit [gatrees.org](https://gatrees.org).
