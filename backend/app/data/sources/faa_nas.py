"""FAA National Airspace System status. Keyless, XML, undocumented.

Advisory data only. Every failure mode returns empty rather than raising.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Any

import httpx

log = logging.getLogger(__name__)

URL = "https://nasstatus.faa.gov/api/airport-status-information"


def _text(node: ET.Element, tag: str) -> str:
    value = node.findtext(tag)
    return value.strip() if value else ""


async def fetch_delays(timeout: float = 8.0) -> dict[str, Any]:
    """Current ground stops, delay programs and closures keyed by airport."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(URL, headers={"User-Agent": "airport-agent/0.1"})
            response.raise_for_status()
        root = ET.fromstring(response.content)
    except Exception as exc:
        log.warning("FAA NAS status unavailable: %s", exc)
        return {}

    airports: dict[str, list[dict[str, str]]] = {}
    for node in root.iter("Airport"):
        # Codes arrive as ICAO (KSFO) or IATA (SFO) depending on the block.
        code = _text(node, "ARPT").upper()
        if len(code) == 4 and code.startswith("K"):
            code = code[1:]
        if not code:
            continue
        airports.setdefault(code, []).append({
            "reason": _text(node, "Reason"),
            "start": _text(node, "Start"),
            "reopen": _text(node, "Reopen"),
        })

    return {"as_of": root.findtext("Update_Time"), "airports": airports}
