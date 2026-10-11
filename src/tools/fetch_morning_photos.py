#!/usr/bin/env python3
"""Fetch attribution-ready historic sports photographs for the Oct 11 morning edition.
The originals are documented in each article. Existing cached assets are left unchanged.
"""
from pathlib import Path
from urllib.request import Request, urlopen
import time
import sys
OUT=Path(__file__).resolve().parents[2] / "assets" / "photos"
PHOTOS=[
  {
    "slot": "mlb",
    "url": "https://thumb.wikimedia.org/wikipedia/commons/thumb/3/35/View_of_American_Family_Field_from_behind_home_plate.jpg/960px-View_of_American_Family_Field_from_behind_home_plate.jpg",
    "file": "View_of_American_Family_Field_from_behind_home_plate.jpg",
    "source": "https://commons.wikimedia.org/wiki/File:View_of_American_Family_Field_from_behind_home_plate.jpg"
  },
  {
    "slot": "nfl",
    "url": "https://thumb.wikimedia.org/wikipedia/commons/thumb/0/03/Lincoln_Financial_Field%2C_Philadelphia%2C_2024.jpg/960px-Lincoln_Financial_Field%2C_Philadelphia%2C_2024.jpg",
    "file": "Lincoln_Financial_Field%2C_Philadelphia%2C_2024.jpg",
    "source": "https://commons.wikimedia.org/wiki/File:Lincoln_Financial_Field,_Philadelphia,_2024.jpg"
  },
  {
    "slot": "mls",
    "url": "https://thumb.wikimedia.org/wikipedia/commons/thumb/9/98/Sergio_Busquets_Maxi_Moralez_NYCFC_Miami_24_Sep_2025-069.jpg/960px-Sergio_Busquets_Maxi_Moralez_NYCFC_Miami_24_Sep_2025-069.jpg",
    "file": "Sergio_Busquets_Maxi_Moralez_NYCFC_Miami_24_Sep_2025-069.jpg",
    "source": "https://commons.wikimedia.org/wiki/File:Sergio_Busquets_Maxi_Moralez_NYCFC_Miami_24_Sep_2025-069.jpg"
  },
  {
    "slot": "nba",
    "url": "https://thumb.wikimedia.org/wikipedia/commons/thumb/2/29/Intuit_Dome_Basketball.jpg/960px-Intuit_Dome_Basketball.jpg",
    "file": "Intuit_Dome_Basketball.jpg",
    "source": "https://commons.wikimedia.org/wiki/File:Intuit_Dome_Basketball.jpg"
  }
]
OUT.mkdir(parents=True,exist_ok=True)
for item in PHOTOS:
    dest=OUT / ("morning-20261011-"+item["slot"]+".jpg")
    if dest.exists() and dest.stat().st_size>10000:
        print("Photo already cached:",dest.name)
        continue
    urls=[item["url"],"https://commons.wikimedia.org/wiki/Special:Redirect/file/"+item["file"]+"?width=960"]
    saved=False
    for link in urls:
        for attempt in range(2):
            try:
                req=Request(link,headers={"User-Agent":"SFANDOM-website-photo-fetch/1.0 (https://sfandom.com/about/)","Accept":"image/jpeg,image/*"})
                with urlopen(req,timeout=35) as resp:
                    data=resp.read()
                if len(data)<10000 or not data.startswith(bytes.fromhex("ffd8")):
                    raise ValueError("Not a valid JPEG thumbnail")
                dest.write_bytes(data)
                print("Saved",dest.name,len(data))
                saved=True
                break
            except Exception as exc:
                print("Retry",dest.name,repr(exc),file=sys.stderr)
                time.sleep(2+attempt)
        if saved:
            break
    if not saved:
        raise SystemExit("Image fetch failed, no empty-photo edition will be published: "+dest.name)
