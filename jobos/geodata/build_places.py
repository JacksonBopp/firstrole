"""Rebuild places.csv.gz from the US Census Gazetteer places file (public domain).

    python jobos/geodata/build_places.py 2024_Gaz_place_national.zip

Source: https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_place_national.zip
Keeps name, state, lat, lon. Strips the legal suffix from names ("Tampa city" -> "Tampa").
"""
import csv
import gzip
import io
import re
import sys
import zipfile
from pathlib import Path

SUFFIX = re.compile(r"(\s+(?:[a-z][a-z'-]*|CDP|\(balance\)))+$")


def clean(name: str) -> str:
    return SUFFIX.sub("", name).strip() or name


def main(src: str) -> None:
    z = zipfile.ZipFile(src)
    raw = z.read(z.namelist()[0])
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    rows = csv.DictReader(io.StringIO(text), delimiter="\t")
    out = Path(__file__).with_name("places.csv.gz")
    seen = set()
    with gzip.open(out, "wt", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "state", "lat", "lon"])
        for r in rows:
            r = {k.strip(): (v or "").strip() for k, v in r.items()}
            key = (clean(r["NAME"]), r["USPS"])
            if key in seen:
                continue
            seen.add(key)
            lat, lon = round(float(r["INTPTLAT"]), 4), round(float(r["INTPTLONG"]), 4)
            w.writerow([key[0], key[1], lat, lon])
            # Consolidated city-counties ("Nashville-Davidson", "Louisville/Jefferson County"): postings say "Nashville"
            if "(balance)" in r["NAME"]:
                short = re.split(r"[-/]", key[0])[0].strip()
                if short != key[0] and (short, key[1]) not in seen:
                    seen.add((short, key[1]))
                    w.writerow([short, key[1], lat, lon])
    print(f"wrote {out} ({len(seen)} places)")


if __name__ == "__main__":
    main(sys.argv[1])
