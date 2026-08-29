"""Download a BTS T-100 Segment (All Carriers) extract into data/raw/.

TranStats serves this from an ASP.NET WebForms page, so there is no static URL:
the page issues __VIEWSTATE / __EVENTVALIDATION tokens that must be echoed back
in the POST. This script does that round trip.

    python scripts/fetch_t100_segment.py            # 2024, all months
    python scripts/fetch_t100_segment.py --year 2023
    python scripts/fetch_t100_segment.py --year 2024 --period 1

Roughly 18 MB and 80 seconds for a full year. The output lands in the gitignored
backend/data/raw/, so the extract is never committed.

Being a scraped form, this breaks if BTS changes the page. When it does,
download by hand from the URL in PAGE below and drop the file in data/raw/ - the
loader does not care how the file got there.
"""

import argparse
import re
import sys
import time
from pathlib import Path

import httpx

PAGE = (
    "https://transtats.bts.gov/DL_SelectFields.aspx"
    "?QO_fu146_anzr=Nv4+Pn44vr45&gnoyr_VQ=FMG"
)
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
TIMEOUT = 600.0


def _token(html: str, name: str) -> str:
    match = re.search(
        r'(?:id|name)=["\']' + name + r'["\'][^>]*value=["\']([^"\']*)["\']', html
    )
    return match.group(1) if match else ""


def fetch(year: str, period: str, geography: str = "All") -> Path:
    client = httpx.Client(
        timeout=TIMEOUT, follow_redirects=True, headers={"user-agent": "Mozilla/5.0"}
    )
    html = client.get(PAGE).text

    # Every data column is a checkbox named after the column in caps; posting
    # them all is equivalent to ticking "select all variables".
    columns = [
        n
        for n in re.findall(r'<input[^>]*type="checkbox"[^>]*name="([^"]+)"', html)
        if n.isupper()
    ]
    if not columns:
        raise RuntimeError(
            "no data columns found - the page layout changed, or the "
            "QO_fu146_anzr parameter was dropped from PAGE"
        )

    form = {
        "__EVENTTARGET": "",
        "__EVENTARGUMENT": "",
        "__LASTFOCUS": "",
        "__VIEWSTATE": _token(html, "__VIEWSTATE"),
        "__VIEWSTATEGENERATOR": _token(html, "__VIEWSTATEGENERATOR"),
        "__EVENTVALIDATION": _token(html, "__EVENTVALIDATION"),
        "cboGeography": geography,
        "cboYear": year,
        "cboPeriod": period,  # "All" for the whole year, else a month number
        "chkDownloadZip": "on",
        "btnDownload": "Download",
    }
    form.update({name: "on" for name in columns})

    print(f"requesting {len(columns)} columns, {geography} {year} period={period} ...")
    started = time.time()
    response = client.post(PAGE, data=form)

    if response.content[:2] != b"PK":
        raise RuntimeError(
            f"expected a zip, got {response.status_code} "
            f"{response.headers.get('content-type')} ({len(response.content)} bytes). "
            "The form rejected the request - check that cboPeriod is 'All' or a "
            "month number, not a month name."
        )

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "" if period == "All" else f"_{period}"
    out = RAW_DIR / f"T100_SEGMENT_ALL_CARRIERS_{year}{suffix}.zip"
    out.write_bytes(response.content)
    print(f"saved {out} ({out.stat().st_size / 1e6:.1f} MB in {time.time() - started:.0f}s)")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", default="2026")
    parser.add_argument("--period", default="All", help="'All' or a month number 1-12")
    parser.add_argument("--geography", default="All")
    args = parser.parse_args()
    try:
        fetch(args.year, args.period, args.geography)
    except Exception as exc:
        print(f"download failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
