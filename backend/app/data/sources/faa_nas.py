"""FAA National Airspace System status. Keyless, XML, undocumented.

Advisory data only. Every failure mode returns empty rather than raising.
"""

from typing import Any

URL = "https://nasstatus.faa.gov/api/airport-status-information"


async def fetch_delays(timeout: float = 8.0) -> dict[str, Any]:
    """Current ground stops, delay programs and closures keyed by airport."""
    raise NotImplementedError
