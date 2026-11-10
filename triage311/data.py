"""Load NYC 311 Service Requests CSV files.

Accepts both formats NYC Open Data produces:
  * the website "Export -> CSV" file   (headers like "Unique Key", "Created Date")
  * the SODA API CSV (resource/erm2-nwe9.csv) (headers like "unique_key", "created_date")
"""

import csv
from datetime import datetime

_COLUMNS = {
    "key": ("Unique Key", "unique_key"),
    "created": ("Created Date", "created_date"),
    "closed": ("Closed Date", "closed_date"),
    "type": ("Complaint Type", "complaint_type"),
    "descriptor": ("Descriptor", "descriptor"),
    "zip": ("Incident Zip", "incident_zip"),
    "borough": ("Borough", "borough"),
    "status": ("Status", "status"),
}

_DATE_FORMATS = ("%m/%d/%Y %I:%M:%S %p", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S")


def parse_date(s):
    s = (s or "").strip()
    if not s:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def read_311(path, limit=None):
    """Yield one plain record per complaint. Rows without a key or created date are skipped."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        col = {}
        for field, names in _COLUMNS.items():
            col[field] = next((n for n in names if n in header), None)
        if col["key"] is None or col["created"] is None:
            raise ValueError(f"{path} does not look like a 311 export (columns: {header[:6]}...)")

        for n, row in enumerate(reader):
            if limit is not None and n >= limit:
                break
            created = parse_date(row[col["created"]])
            key = (row[col["key"]] or "").strip()
            if not key or created is None:
                continue
            yield {
                "key": int(key) if key.isdigit() else key,
                "created": created,
                "closed": parse_date(row[col["closed"]]) if col["closed"] else None,
                "type": (row[col["type"]] or "").strip() if col["type"] else "",
                "descriptor": (row[col["descriptor"]] or "").strip() if col["descriptor"] else "",
                "zip": (row[col["zip"]] or "").strip()[:5] if col["zip"] else "",
                "borough": (row[col["borough"]] or "").strip() if col["borough"] else "",
                "status": (row[col["status"]] or "").strip() if col["status"] else "",
            }
