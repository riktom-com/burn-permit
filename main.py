import asyncio
import re
import sqlite3
from datetime import datetime, timezone, date, timedelta
from pathlib import Path

import httpx
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://burn.riktom.com"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

HEADERS = {"User-Agent": "BurnPermitChecker/1.0 (+https://burn.riktom.com; contact tommy@nijemtech.com)"}
DB_PATH = Path("/opt/burn-permit/history.db")

# ── Database ──────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gfc_readings (
                read_date  TEXT PRIMARY KEY,
                class      TEXT NOT NULL,
                level      INTEGER NOT NULL,
                scraped_at TEXT NOT NULL
            )
        """)

init_db()

def store_gfc(read_date: str, class_: str, level: int):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO gfc_readings (read_date, class, level, scraped_at) VALUES (?,?,?,?)",
            (read_date, class_, level, datetime.now(timezone.utc).isoformat())
        )

def get_stored_gfc(read_date: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT class, level FROM gfc_readings WHERE read_date = ?", (read_date,)
        ).fetchone()
    if row:
        return {"class": row["class"], "level": row["level"]}
    return None

# ── County / FIPS data ────────────────────────────────────────────────────────

GA_COUNTIES = {
    "Appling": "GAC001", "Atkinson": "GAC003", "Bacon": "GAC005", "Baker": "GAC007",
    "Baldwin": "GAC009", "Banks": "GAC011", "Barrow": "GAC013", "Bartow": "GAC015",
    "Ben Hill": "GAC017", "Berrien": "GAC019", "Bibb": "GAC021", "Bleckley": "GAC023",
    "Brantley": "GAC025", "Brooks": "GAC027", "Bryan": "GAC029", "Bulloch": "GAC031",
    "Burke": "GAC033", "Butts": "GAC035", "Calhoun": "GAC037", "Camden": "GAC039",
    "Candler": "GAC043", "Carroll": "GAC045", "Catoosa": "GAC047", "Charlton": "GAC049",
    "Chatham": "GAC051", "Chattahoochee": "GAC053", "Chattooga": "GAC055",
    "Cherokee": "GAC057", "Clarke": "GAC059", "Clay": "GAC061", "Clayton": "GAC063",
    "Clinch": "GAC065", "Cobb": "GAC067", "Coffee": "GAC069", "Colquitt": "GAC071",
    "Columbia": "GAC073", "Cook": "GAC075", "Coweta": "GAC077", "Crawford": "GAC079",
    "Crisp": "GAC081", "Dade": "GAC083", "Dawson": "GAC085", "Decatur": "GAC087",
    "DeKalb": "GAC089", "Dodge": "GAC091", "Dooly": "GAC093", "Dougherty": "GAC095",
    "Douglas": "GAC097", "Early": "GAC099", "Echols": "GAC101", "Effingham": "GAC103",
    "Elbert": "GAC105", "Emanuel": "GAC107", "Evans": "GAC109", "Fannin": "GAC111",
    "Fayette": "GAC113", "Floyd": "GAC115", "Forsyth": "GAC117", "Franklin": "GAC119",
    "Fulton": "GAC121", "Gilmer": "GAC123", "Glascock": "GAC125", "Glynn": "GAC127",
    "Gordon": "GAC129", "Grady": "GAC131", "Greene": "GAC133", "Gwinnett": "GAC135",
    "Habersham": "GAC137", "Hall": "GAC139", "Hancock": "GAC141", "Haralson": "GAC143",
    "Harris": "GAC145", "Hart": "GAC147", "Heard": "GAC149", "Henry": "GAC151",
    "Houston": "GAC153", "Irwin": "GAC155", "Jackson": "GAC157", "Jasper": "GAC159",
    "Jeff Davis": "GAC161", "Jefferson": "GAC163", "Jenkins": "GAC165", "Johnson": "GAC167",
    "Jones": "GAC169", "Lamar": "GAC171", "Lanier": "GAC173", "Laurens": "GAC175",
    "Lee": "GAC177", "Liberty": "GAC179", "Lincoln": "GAC181", "Long": "GAC183",
    "Lowndes": "GAC185", "Lumpkin": "GAC187", "McDuffie": "GAC189", "McIntosh": "GAC191",
    "Macon": "GAC193", "Madison": "GAC195", "Marion": "GAC197", "Meriwether": "GAC199",
    "Miller": "GAC201", "Mitchell": "GAC205", "Monroe": "GAC207", "Montgomery": "GAC209",
    "Morgan": "GAC211", "Murray": "GAC213", "Muscogee": "GAC215", "Newton": "GAC217",
    "Oconee": "GAC219", "Oglethorpe": "GAC221", "Paulding": "GAC223", "Peach": "GAC225",
    "Pickens": "GAC227", "Pierce": "GAC229", "Pike": "GAC231", "Polk": "GAC233",
    "Pulaski": "GAC235", "Putnam": "GAC237", "Quitman": "GAC239", "Rabun": "GAC241",
    "Randolph": "GAC243", "Richmond": "GAC245", "Rockdale": "GAC247", "Schley": "GAC249",
    "Screven": "GAC251", "Seminole": "GAC253", "Spalding": "GAC255", "Stephens": "GAC257",
    "Stewart": "GAC259", "Sumter": "GAC261", "Talbot": "GAC263", "Taliaferro": "GAC265",
    "Tattnall": "GAC267", "Taylor": "GAC269", "Telfair": "GAC271", "Terrell": "GAC273",
    "Thomas": "GAC275", "Tift": "GAC277", "Toombs": "GAC279", "Towns": "GAC281",
    "Treutlen": "GAC283", "Troup": "GAC285", "Turner": "GAC287", "Twiggs": "GAC289",
    "Union": "GAC291", "Upson": "GAC293", "Walker": "GAC295", "Walton": "GAC297",
    "Ware": "GAC299", "Warren": "GAC301", "Washington": "GAC303", "Wayne": "GAC305",
    "Webster": "GAC307", "Wheeler": "GAC309", "White": "GAC311", "Whitfield": "GAC313",
    "Wilcox": "GAC315", "Wilkes": "GAC317", "Wilkinson": "GAC319", "Worth": "GAC321",
}

FIRE_ALERT_EVENTS = {"Red Flag Warning", "Fire Weather Watch", "Extreme Fire Danger"}

# ── Geocoding ─────────────────────────────────────────────────────────────────

async def zip_to_county(zipcode: str) -> dict:
    url = (
        f"https://nominatim.openstreetmap.org/search"
        f"?postalcode={zipcode}&country=US&format=json&addressdetails=1&limit=1"
    )
    try:
        async with httpx.AsyncClient(timeout=10, headers=HEADERS) as client:
            r = await client.get(url)
            r.raise_for_status()
        data = r.json()
        if not data:
            return {"error": "ZIP code not found."}
        addr = data[0].get("address", {})
        state = addr.get("state", "")
        if state != "Georgia":
            return {"error": f"ZIP {zipcode} is in {state or 'an unknown state'}, not Georgia. This tool covers Georgia only."}
        raw_county = addr.get("county", "")
        county = raw_county.replace(" County", "").strip()
        if county not in GA_COUNTIES:
            return {"error": f"Could not match '{county}' to a Georgia county."}
        return {
            "county": county,
            "lat": float(data[0]["lat"]),
            "lon": float(data[0]["lon"]),
        }
    except Exception as e:
        return {"error": "Geocoding unavailable. Please select your county manually."}

# ── NWS Alerts ────────────────────────────────────────────────────────────────

async def get_nws_alerts(county_fips: str, check_date: str | None = None) -> list:
    if check_date and check_date != date.today().isoformat():
        d = date.fromisoformat(check_date)
        start = f"{d.isoformat()}T00:00:00Z"
        end   = f"{d.isoformat()}T23:59:59Z"
        url = f"https://api.weather.gov/alerts?zone={county_fips}&start={start}&end={end}"
    else:
        url = f"https://api.weather.gov/alerts/active?zone={county_fips}"
    try:
        async with httpx.AsyncClient(timeout=10, headers=HEADERS) as client:
            r = await client.get(url)
            r.raise_for_status()
        data = r.json()
        alerts = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            event = props.get("event", "")
            if any(e.lower() in event.lower() for e in FIRE_ALERT_EVENTS):
                alerts.append({
                    "event": event,
                    "headline": props.get("headline", ""),
                    "description": (props.get("description", "") or "")[:400],
                    "expires": props.get("expires", ""),
                })
        return alerts
    except Exception:
        return []

# ── GFC Burn Ban (firesponse API) ─────────────────────────────────────────────

GFC_BAN_URL = (
    "https://georgiafc.firesponse.com/burn-permit/api/burnrestriction/all/public"
    "?levels=PUBLIC&levels=PRIVATE_PUBLIC"
)
GFC_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://georgiafc.firesponse.com/public/",
}

async def get_gfc_burn_ban(county: str) -> dict:
    """Check the GFC firesponse API for an active burn ban in the given county."""
    try:
        async with httpx.AsyncClient(timeout=10, headers=GFC_HEADERS) as client:
            r = await client.get(GFC_BAN_URL)
            r.raise_for_status()
        bans = r.json()
        # Match county name case-insensitively
        county_lower = county.lower()
        for ban in bans:
            name = ban.get("Name", "").lower()
            # County ban names sometimes include city names too (e.g. "Lowndes")
            if name == county_lower or name.startswith(county_lower):
                return {
                    "active": True,
                    "name": ban.get("Name", county),
                    "has_exemption": ban.get("hasExemption", False),
                }
        return {"active": False}
    except Exception as exc:
        return {"active": None, "error": str(exc)}  # None = could not determine

# ── GFC Fire Danger ───────────────────────────────────────────────────────────

async def get_gfc_danger(check_date: str | None = None) -> dict:
    today = date.today().isoformat()
    target = check_date or today

    stored = get_stored_gfc(target)
    if stored:
        return stored

    if target != today:
        return {"class": "Not Available", "level": 0,
                "note": "GFC historical data is only available from the date this tool launched."}

    url = "https://weather.gfc.state.ga.us/Current2/GARAWS-NFDSUM24.aspx"
    south_ga_stations = ["camilla", "bainbridge", "adel", "waycross",
                         "folkston", "nahunta", "douglas", "tifton", "albany",
                         "baxley", "vidalia", "okefenokee"]
    class_labels = {1: "Low", 2: "Moderate", 3: "High", 4: "Very High", 5: "Extreme"}

    try:
        async with httpx.AsyncClient(timeout=15, headers=HEADERS) as client:
            r = await client.get(url)
            r.raise_for_status()
        text = r.text
        text_lower = text.lower()

        highest = 0
        highest_label = "Unknown"

        for station in south_ga_stations:
            idx = text_lower.find(station)
            if idx < 0:
                continue
            snippet = text[idx:idx+1200]
            nums = re.findall(r"<td[^>]*>.*?(\d+).*?</td>", snippet, re.DOTALL)
            if len(nums) >= 7:
                try:
                    class_day = int(nums[6])
                    if 1 <= class_day <= 5 and class_day > highest:
                        highest = class_day
                        highest_label = class_labels[class_day]
                except ValueError:
                    pass

        result = {"class": highest_label, "level": highest}
        if highest > 0:
            store_gfc(today, highest_label, highest)
        return result
    except Exception:
        return {"class": "Unavailable", "level": 0}

# ── Recommendation ────────────────────────────────────────────────────────────

def build_recommendation(alerts: list, gfc: dict, burn_ban: dict) -> dict:
    has_red_flag  = any("red flag warning" in a["event"].lower() for a in alerts)
    has_watch     = any("watch" in a["event"].lower() for a in alerts)
    level         = gfc.get("level", 0)
    ban_active    = burn_ban.get("active")  # True / False / None (unknown)
    has_exemption = burn_ban.get("has_exemption", False)

    # GFC burn ban is the hardest stop — overrides everything
    if ban_active is True and not has_exemption:
        return {
            "status": "banned", "color": "red", "icon": "🚫",
            "title": "Burn Ban in Effect",
            "summary": (
                f"The Georgia Forestry Commission has an active burn ban for {burn_ban.get('name', 'your county')}. "
                "Open burning is not permitted. Contact your local GFC office or call "
                "1-800-GA-TREES for details."
            ),
        }
    if ban_active is True and has_exemption:
        return {
            "status": "caution", "color": "orange", "icon": "⚠️",
            "title": "Burn Ban — Exemptions May Apply",
            "summary": (
                f"A GFC burn ban is active for {burn_ban.get('name', 'your county')} but exemptions may be available. "
                "Call 1-800-GA-TREES or visit gatrees.org to find out if your burn qualifies."
            ),
        }
    if has_red_flag or level >= 4:
        return {
            "status": "restricted", "color": "red", "icon": "🚫",
            "title": "Burning Likely Restricted",
            "summary": ("A Red Flag Warning is in effect or fire danger is Very High/Extreme. "
                        "The Georgia Forestry Commission typically suspends burn permits under these conditions. "
                        "Contact your local GFC office or call 1-800-GA-TREES before burning."),
        }
    elif has_watch or level == 3:
        return {
            "status": "caution", "color": "orange", "icon": "⚠️",
            "title": "Use Caution — Elevated Fire Danger",
            "summary": ("A Fire Weather Watch is in effect or fire danger is High. "
                        "Permits may be available but conditions can change quickly. "
                        "Verify your permit status at 1-800-GA-TREES before burning."),
        }
    elif level > 0:
        return {
            "status": "ok", "color": "green", "icon": "✅",
            "title": "Conditions Appear Favorable",
            "summary": (f"Fire danger is {gfc['class']} with no active fire weather alerts or GFC burn ban "
                        "for your county. A burn permit is still required by Georgia law. "
                        "Get yours free at 1-800-GA-TREES or online through the Georgia Forestry Commission."),
        }
    else:
        return {
            "status": "unknown", "color": "gray", "icon": "❓",
            "title": "Check with GFC Directly",
            "summary": ("Fire danger data is temporarily unavailable. "
                        "Call 1-800-GA-TREES or visit gatrees.org to check current conditions "
                        "and obtain your free burn permit before burning."),
        }

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/burn/geocode")
async def geocode(zip: str = Query(..., min_length=5, max_length=5)):
    if not zip.isdigit():
        raise HTTPException(400, "ZIP code must be 5 digits.")
    return await zip_to_county(zip)

@app.get("/api/burn")
async def burn_check(
    county:     str           = Query(...),
    check_date: str | None    = Query(None),
):
    county = county.strip().title()
    fips = GA_COUNTIES.get(county)
    if not fips:
        raise HTTPException(400, f"County '{county}' not found.")

    today = date.today().isoformat()

    if check_date:
        try:
            d = date.fromisoformat(check_date)
            if d > date.today():
                check_date = today
        except ValueError:
            check_date = None

    is_today = (check_date or today) == today

    # Fetch all three data sources in parallel; burn ban only for today
    if is_today:
        alerts, gfc, burn_ban = await asyncio.gather(
            get_nws_alerts(fips, check_date),
            get_gfc_danger(check_date),
            get_gfc_burn_ban(county),
        )
    else:
        alerts, gfc = await asyncio.gather(
            get_nws_alerts(fips, check_date),
            get_gfc_danger(check_date),
        )
        burn_ban = {"active": None, "note": "Burn ban history not available for past dates."}

    return {
        "county":      county,
        "date":        check_date or today,
        "is_today":    is_today,
        "checked_at":  datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "recommendation": build_recommendation(alerts, gfc, burn_ban),
        "alerts":      alerts,
        "fire_danger": gfc,
        "burn_ban":    burn_ban,
    }

@app.get("/api/burn/counties")
async def list_counties():
    return sorted(GA_COUNTIES.keys())

@app.get("/api/burn/health")
async def health():
    return {"ok": True}
