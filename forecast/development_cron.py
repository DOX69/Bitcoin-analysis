"""Run the existing Development ingestion cron at 07:00 Europe/Paris."""

from datetime import datetime, timezone
import argparse
import json
import os
from zoneinfo import ZoneInfo


def due(now):
    return now.astimezone(ZoneInfo("Europe/Paris")).hour == 7


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Manually run with the real clock, without waiting for 07:00",
    )
    args = parser.parse_args()
    if os.environ.get("RAILWAY_ENVIRONMENT_NAME", "").lower() != "development":
        raise ValueError("This entry point is restricted to Railway Development")
    now = datetime.now(timezone.utc)
    if not args.run_now and not due(now):
        print(json.dumps({"status": "outside_paris_07_hour", "utc": now.isoformat()}))
        return
    from raw_ingest.orchestrator import main as ingest

    ingest()


if __name__ == "__main__":
    main()
