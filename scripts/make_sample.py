"""Generate a synthetic file in the NYC Open Data 311 export format.

Only for development and CI when the real file is not available.
All results in the report should use the real dataset.

    python scripts/make_sample.py data/sample.csv 50000
"""

import csv
import random
import sys
from datetime import datetime, timedelta

TYPES = [
    ("Noise - Residential", "Loud Music/Party", 18), ("Illegal Parking", "Blocked Hydrant", 14),
    ("HEAT/HOT WATER", "ENTIRE BUILDING", 12), ("Blocked Driveway", "No Access", 9),
    ("Street Condition", "Pothole", 7), ("Noise - Street/Sidewalk", "Loud Talking", 7),
    ("UNSANITARY CONDITION", "PESTS", 5), ("Water System", "Leak (Use Comments)", 4),
    ("Abandoned Vehicle", "With License Plate", 4), ("PLUMBING", "WATER SUPPLY", 4),
    ("Dirty Condition", "Trash", 4), ("Traffic Signal Condition", "Controller", 3),
    ("Elevator", "Elevator - Defective/Not Working", 2), ("Graffiti", "Graffiti", 2),
    ("Gas Leak", "Gas Leak", 1),
]
ZIPS = [("11201", "BROOKLYN"), ("11211", "BROOKLYN"), ("11226", "BROOKLYN"), ("10025", "MANHATTAN"),
        ("10002", "MANHATTAN"), ("10467", "BRONX"), ("10458", "BRONX"), ("11368", "QUEENS"),
        ("11375", "QUEENS"), ("10314", "STATEN ISLAND")]
FMT = "%m/%d/%Y %I:%M:%S %p"


def main(path, n, seed=7):
    rng = random.Random(seed)
    start = datetime(2025, 7, 1)
    weights = [w for *_, w in TYPES]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Unique Key", "Created Date", "Closed Date", "Complaint Type", "Descriptor",
                    "Incident Zip", "Borough", "Status"])
        for i in range(n):
            ctype, desc, _ = rng.choices(TYPES, weights)[0]
            zipc, boro = rng.choice(ZIPS)
            created = start + timedelta(seconds=rng.randint(0, 7 * 86400))
            if rng.random() < 0.85:
                closed = created + timedelta(minutes=rng.expovariate(1 / 600))
                closed_s, status = closed.strftime(FMT), "Closed"
            else:
                closed_s, status = "", "Open"
            w.writerow([65000000 + i, created.strftime(FMT), closed_s, ctype, desc, zipc, boro, status])


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 50000)
