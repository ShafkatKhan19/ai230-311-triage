"""Triage engine, CSV loader and CLI, on small hand-written data."""
from datetime import datetime

import pytest

from triage311 import cli
from triage311.data import parse_date, read_311
from triage311.engine import ESCALATION_STEP, TriageEngine


def rec(key, created, closed=None, ctype="Noise - Residential", zip_code="11201"):
    return {"key": key, "created": created, "closed": closed, "type": ctype,
            "descriptor": "", "zip": zip_code, "borough": "BROOKLYN", "status": ""}


T = lambda h, m=0: datetime(2025, 7, 1, h, m)  # noqa: E731


@pytest.fixture
def engine():
    e = TriageEngine()
    e.add(rec(1, T(8), ctype="Noise - Residential"))            # weight 2, open
    e.add(rec(2, T(9), ctype="HEAT/HOT WATER"))                 # weight 8, open
    e.add(rec(3, T(10), ctype="Elevator"))                      # weight 8, newer than 2
    e.add(rec(4, T(7), closed=T(11), ctype="HEAT/HOT WATER"))   # closes at 11:00
    e.add(rec(5, T(13), ctype="Graffiti", zip_code="10025"))    # created after noon
    e.add(rec(6, T(6), ctype="Something Unlisted"))             # default weight 1
    return e


def test_replay_reconstructs_open_set_at_a_time(engine):
    assert engine.replay(T(10, 30)) == (5, 0)          # 4 not yet closed, 5 not yet created
    assert [k for k, _ in engine.next(10)] == [4, 2, 3, 1, 6]
    assert engine.replay(T(12)) == (5, 1)              # 4 has closed
    assert [k for k, _ in engine.next(10)] == [2, 3, 1, 6]
    pushes, removes = engine.replay(T(23))
    assert (pushes, removes) == (6, 1) and len(engine.queue) == 5


def test_order_is_weight_then_oldest_then_key(engine):
    engine.replay(T(23))
    # 2 and 3 both weigh 8, 2 is older; 1 (w=2) beats 5 and 6 (w=1); 6 is older than 5.
    assert [k for k, _ in engine.next(10)] == [2, 3, 1, 6, 5]


def test_escalate_and_close(engine):
    engine.replay(T(23))
    engine.escalate(6)
    engine.escalate(6)
    engine.escalate(6)                                  # 1 + 3 * 3 = 10 > 8
    assert engine.weight[6] == 1 + 3 * ESCALATION_STEP
    assert engine.next(1)[0][0] == 6
    engine.close(6)
    assert engine.next(1)[0][0] == 2 and 6 not in engine.queue
    assert engine.lookup(6)["type"] == "Something Unlisted"   # record is kept
    with pytest.raises(KeyError):
        engine.escalate(6)
    with pytest.raises(KeyError):
        engine.close(6)
    with pytest.raises(KeyError):
        engine.escalate(4)                              # closed before the replay time
    engine.queue.check_invariants()


def test_counts_and_duplicate_rows(engine):
    assert engine.count("11201", "HEAT/HOT WATER") == 2
    assert engine.count("10025", "Graffiti") == 1
    assert engine.count("99999", "Graffiti") == 0
    assert engine.add(rec(2, T(9), ctype="HEAT/HOT WATER")) is False   # same key again
    assert engine.count("11201", "HEAT/HOT WATER") == 2 and len(engine.records) == 6
    assert engine.lookup(12345) is None


def test_closed_before_created_is_treated_as_open():
    e = TriageEngine()
    e.add(rec(1, T(9), closed=T(8)))                    # bad row: closes before it opens
    assert e.replay(T(23)) == (1, 0) and 1 in e.queue


# ---------------------------------------------------------------- loader
EXPORT = ("Unique Key,Created Date,Closed Date,Complaint Type,Descriptor,Incident Zip,Borough,Status\n"
          "101,07/01/2025 08:00:00 AM,07/01/2025 09:30:00 PM,HEAT/HOT WATER,ENTIRE BUILDING,11201-1234,BROOKLYN,Closed\n"
          "102,07/01/2025 12:15:00 PM,,Noise - Residential,Loud Music/Party,10025,MANHATTAN,Open\n"
          ",07/01/2025 12:15:00 PM,,Noise,,10025,MANHATTAN,Open\n"
          "104,not a date,,Noise,,10025,MANHATTAN,Open\n")
API = ("unique_key,created_date,closed_date,complaint_type,descriptor,incident_zip,borough,status\n"
       "201,2025-07-01T08:00:00.000,2025-07-01T21:30:00.000,HEAT/HOT WATER,ENTIRE BUILDING,11201,BROOKLYN,Closed\n"
       "202,2025-07-01T12:15:00.000,,Noise - Residential,Loud Music/Party,,MANHATTAN,Open\n")


def test_loader_reads_both_formats_and_skips_bad_rows(tmp_path):
    p = tmp_path / "export.csv"
    p.write_text(EXPORT, encoding="utf-8")
    rows = list(read_311(p))
    assert [r["key"] for r in rows] == [101, 102]       # no key / unparseable date are skipped
    assert rows[0]["created"] == datetime(2025, 7, 1, 8) and rows[0]["closed"] == datetime(2025, 7, 1, 21, 30)
    assert rows[0]["zip"] == "11201" and rows[1]["closed"] is None

    q = tmp_path / "api.csv"
    q.write_text(API, encoding="utf-8")
    api_rows = list(read_311(q))
    assert api_rows[0]["created"] == rows[0]["created"] and api_rows[0]["closed"] == rows[0]["closed"]
    assert api_rows[1]["zip"] == "" and len(list(read_311(q, limit=1))) == 1


def test_loader_rejects_other_csv_files(tmp_path):
    p = tmp_path / "other.csv"
    p.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        list(read_311(p))
    assert parse_date("") is None and parse_date(None) is None


# ---------------------------------------------------------------- CLI
def test_cli_session(tmp_path, monkeypatch, capsys):
    p = tmp_path / "export.csv"
    p.write_text(EXPORT, encoding="utf-8")
    commands = iter(["next 5", "lookup 101", "lookup 999", "escalate 102", "escalate", "close 102",
                     "close 102", "count 11201 HEAT/HOT WATER", "stats", "bogus", "quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(commands))
    cli.main([str(p), "--at", "2025-07-01 13:00"])
    out = capsys.readouterr().out
    assert "Loaded 2 complaints" in out and "2 opened, 0 closed, 2 still open" in out
    assert "not found" in out and "escalated 102 to weight 5" in out
    assert "usage: escalate" in out and "error:" in out      # second close fails cleanly
    assert "\n1\n" in out                                    # the count
