"""Quick smoke test: fetch from all sources, filter, print results (no Slack)."""
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)s: %(message)s")

from filters import filter_jobs, parse_experience
from scrapers import ALL_SCRAPERS

print("parse_experience('0-2 years') ->", parse_experience("0-2 years"))
print("parse_experience('fresher') ->", parse_experience("fresher"))
print("parse_experience(None) ->", parse_experience(None))

raw = []
for name, cls in ALL_SCRAPERS.items():
    try:
        found = cls().fetch(["python"], ["remote", "India"], 2)
        print(f"{name}: {len(found)} jobs fetched")
        raw += found
    except Exception as e:
        print(f"{name} FAILED: {e}")

matches = filter_jobs(raw, ["python"], ["remote", "India"], 2)
print(f"total={len(raw)} after_filters={len(matches)}")
for j in matches[:10]:
    print("  -", j.title, "|", j.company, "|", j.location, "|", j.source)
