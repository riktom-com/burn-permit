import re, sqlite3, httpx
from datetime import date, datetime, timezone
from pathlib import Path

DB_PATH = Path('/opt/burn-permit/history.db')
HEADERS = {'User-Agent': 'BurnPermitChecker/1.0 (+https://burn.riktom.com)'}
STATIONS = ['camilla','bainbridge','adel','waycross','folkston','nahunta','douglas','tifton','albany','baxley']
LABELS   = {1:'Low',2:'Moderate',3:'High',4:'Very High',5:'Extreme'}

def run():
    r = httpx.get('https://weather.gfc.state.ga.us/Current2/GARAWS-NFDSUM24.aspx', headers=HEADERS, timeout=15, follow_redirects=True)
    text = r.text; tl = text.lower()
    highest = 0; label = 'Unknown'
    for st in STATIONS:
        idx = tl.find(st)
        if idx < 0: continue
        nums = re.findall(r'<td[^>]*>.*?(\d+).*?</td>', text[idx:idx+1200], re.DOTALL)
        if len(nums) >= 7:
            try:
                cd = int(nums[6])
                if 1 <= cd <= 5 and cd > highest:
                    highest = cd; label = LABELS[cd]
            except: pass
    if highest > 0:
        today = date.today().isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('INSERT OR REPLACE INTO gfc_readings (read_date,class,level,scraped_at) VALUES (?,?,?,?)',
                         (today, label, highest, datetime.now(timezone.utc).isoformat()))
        print(f'{today}: {label} ({highest})')
    else:
        print('No data found')

run()
