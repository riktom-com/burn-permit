# Burn Permit Checker — CLAUDE.md

## Project
Georgia Forestry Commission burn permit conditions checker for all 159 Georgia counties.
Part of the **riktom.com** venture by Tommy Nijem and Ricky Browning.

## Deploy Target
- Production: `burn.riktom.com`
- Backend: FastAPI on `127.0.0.1:8007` as systemd unit `burn-permit-api.service`
- Frontend: Static HTML served by nginx from `/opt/burn-permit/`
- nginx config: `/etc/nginx/sites-enabled/burn.riktom.com`

## Stack
- **Backend:** Python 3.12, FastAPI, httpx, SQLite
- **Frontend:** Vanilla HTML/CSS/JS

## Data Sources

| Source | What it provides | Notes |
|--------|-----------------|-------|
| GFC firesponse API | **Active county burn bans** (highest priority) | `https://georgiafc.firesponse.com/burn-permit/api/burnrestriction/all/public?levels=PUBLIC&levels=PRIVATE_PUBLIC` — returns JSON array of all active bans by county name. No auth required. |
| NWS api.weather.gov | Red Flag Warnings, Fire Weather Watches | Queried by county FIPS (GAC###) |
| GFC NFDSUM page | Daily fire danger class (1–5) | `https://weather.gfc.state.ga.us/Current2/GARAWS-NFDSUM24.aspx` — **Cloudflare-blocked from VPS IP** as of 2026-05-12. Falls back to SQLite history. |

## Important: Cloudflare Block
`gatrees.org` and `weather.gfc.state.ga.us` return 403 from the VPS IP (Cloudflare block).
The GFC fire danger scraper (`scrape_gfc.py` / `gfc-scraper.timer`) will fail silently.
The firesponse burn ban API (`georgiafc.firesponse.com`) is NOT behind Cloudflare and works fine.

## Recommendation Logic (priority order)
1. **GFC burn ban active (no exemption)** → 🚫 Burn Ban in Effect (red)
2. **GFC burn ban active (with exemption)** → ⚠️ Burn Ban — Exemptions May Apply (orange)
3. **NWS Red Flag Warning OR fire danger ≥ 4** → 🚫 Burning Likely Restricted (red)
4. **NWS Fire Weather Watch OR fire danger = 3** → ⚠️ Use Caution (orange)
5. **Fire danger 1–2, no ban** → ✅ Conditions Appear Favorable (green)
6. **No data** → ❓ Check with GFC Directly (gray)

## API Routes
| Route | Description |
|-------|-------------|
| `GET /api/burn?county=Lowndes` | Main check — returns recommendation, alerts, fire danger, burn ban |
| `GET /api/burn?county=Lowndes&check_date=2026-05-10` | Historical check (NWS + stored GFC only; burn ban not available for past dates) |
| `GET /api/burn/geocode?zip=31601` | ZIP → county via Nominatim |
| `GET /api/burn/counties` | List all 159 GA counties |
| `GET /api/burn/health` | Health check |

## Database
- SQLite at `/opt/burn-permit/history.db`
- Table: `gfc_readings (read_date TEXT PK, class TEXT, level INT, scraped_at TEXT)`
- Populated by `scrape_gfc.py` via `gfc-scraper.timer` at 19:05 UTC daily
- GFC scraper currently failing due to Cloudflare block — history only has data from before the block

## Secrets
- No secrets required — all data sources are public APIs

## Deploy
```bash
systemctl restart burn-permit-api
journalctl -u burn-permit-api -f
```


## Standardized Nav (rk-nav)

This app uses the shared riktom.com nav block (scoped `.rk-*` classes, self-contained CSS) that is identical across all 11 riktom.com properties. The block is enclosed by marker comments:

```
<!-- rk-nav:start -->
... nav HTML + scoped style ...
<!-- rk-nav:end -->
```

**To update the nav site-wide** (add a new app, change a link, restyle):
1. Edit `/tmp/patch_navs.py` on the VPS (or `/tmp/sync/patch_local.py` for local repos) with the new HTML.
2. Re-run the patcher — it finds the markers and replaces the block in place. The replace is idempotent.
3. For repos with React/Vite builds (e.g. fire-watcher), re-patch after rebuild since `dist/index.html` is regenerated.

Nav contents: Logo · About · Blog · Apps ▾ (11 apps) · 💡 Suggest · 🏠 Home (top-right white pill).
