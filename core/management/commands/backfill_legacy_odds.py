"""One-shot: backfill `PredictionLog.odds` for rows recommended before commit
c91c350 (2026-05-13) when the write path started capturing bet-time odds.

Fetches historical O/U 2.5 odds from SportMonks (market_id=80, total='2.5') and
picks the median across bookmakers for the predicted side. Also handles the 2
legacy 1x2 rows (uses market_id=1 odds for the predicted outcome).

Recomputes `profit_loss_10` and `roi_percent` via `PredictionLog.calculate_performance()`.

Usage:
    python manage.py backfill_legacy_odds --dry-run          # report only
    python manage.py backfill_legacy_odds --dry-run --limit 5
    python manage.py backfill_legacy_odds                    # apply changes
"""
import os
import statistics
import time

import requests
import urllib3
from django.core.management.base import BaseCommand
from django.db import transaction

# One-shot script hits SportMonks from a workstation that may not have a
# usable cert bundle. Suppress the warning + skip verification for this run.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from core.models import PredictionLog


SPORTMONKS_BASE = "https://api.sportmonks.com/v3/football"


class Command(BaseCommand):
    help = "Backfill odds/profit_loss for legacy PredictionLog rows missing odds."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would change; do not write to DB.")
        parser.add_argument("--limit", type=int, default=None,
                            help="Cap rows processed (useful for smoke testing).")
        parser.add_argument("--sleep", type=float, default=0.15,
                            help="Seconds to sleep between SportMonks calls.")

    def handle(self, *args, **options):
        api_key = os.environ.get("SPORTMONKS_API_TOKEN") or os.environ.get("SPORTMONKS_KEY")
        if not api_key:
            self.stderr.write(self.style.ERROR("SPORTMONKS_API_TOKEN env var not set"))
            return

        dry_run = options["dry_run"]
        limit = options["limit"]
        sleep_s = options["sleep"]

        # Legacy universe: recommended, resolved, no valid odds.
        # Order oldest first so failures don't leave a temporal gap.
        qs = (PredictionLog.objects
              .filter(is_recommended=True, actual_outcome__isnull=False)
              .exclude(actual_outcome="")
              .exclude(match_status="archived")
              .exclude(is_audit_excluded=True)
              .filter(odds__isnull=True) | PredictionLog.objects
              .filter(is_recommended=True, actual_outcome__isnull=False)
              .exclude(actual_outcome="")
              .exclude(match_status="archived")
              .exclude(is_audit_excluded=True)
              .filter(odds=0))
        # Deduplicate & order
        qs = qs.distinct().order_by("prediction_logged_at")
        if limit:
            qs = qs[:limit]

        total = qs.count()
        self.stdout.write(f"Processing {total} legacy rows (dry_run={dry_run})")

        stats = {
            "attempted": 0, "updated": 0,
            "no_odds_in_response": 0,
            "no_match_for_outcome": 0,
            "sportmonks_error": 0,
            "wrong_market": 0,
        }

        for row in qs.iterator():
            stats["attempted"] += 1
            fixture_id = row.fixture_id
            market_type = row.market_type or "1x2"
            predicted = (row.predicted_outcome or "").lower().strip()

            try:
                resp = requests.get(
                    f"{SPORTMONKS_BASE}/fixtures/{fixture_id}",
                    params={"api_token": api_key, "include": "odds"},
                    timeout=15,
                    verify=False,
                )
            except requests.RequestException as e:
                stats["sportmonks_error"] += 1
                self.stderr.write(f"  [{fixture_id}] request failed: {e}")
                time.sleep(sleep_s)
                continue

            if resp.status_code != 200:
                stats["sportmonks_error"] += 1
                self.stderr.write(f"  [{fixture_id}] HTTP {resp.status_code}")
                time.sleep(sleep_s)
                continue

            data = resp.json().get("data", {}) or {}
            odds_list = data.get("odds") or []

            picked = self._pick_odds(odds_list, market_type, predicted)
            if picked is None:
                key = "no_odds_in_response" if not odds_list else "no_match_for_outcome"
                stats[key] += 1
                self.stdout.write(f"  [{fixture_id}] {market_type}/{predicted}: no match ({key})")
                time.sleep(sleep_s)
                continue

            median_value, bookmaker_id, sample_size = picked

            old_odds = row.odds
            old_pl = row.profit_loss_10
            old_roi = row.roi_percent

            self.stdout.write(
                f"  [{fixture_id}] {market_type}/{predicted}: "
                f"odds {old_odds!r} -> {median_value:.2f} "
                f"(median of {sample_size} bookmakers, bkm_id={bookmaker_id}); "
                f"old P/L={old_pl}"
            )

            if not dry_run:
                with transaction.atomic():
                    row.odds = median_value
                    row.bookmaker = f"SportMonks-median (bkm {bookmaker_id})"
                    # Rerun P/L via the model method (writes was_correct + profit_loss_10 + roi_percent)
                    row.calculate_performance()
                    row.save(update_fields=[
                        "odds", "bookmaker", "was_correct",
                        "profit_loss_10", "roi_percent",
                    ])
                stats["updated"] += 1
                self.stdout.write(
                    f"    -> new P/L={row.profit_loss_10:.2f} "
                    f"(was {old_pl}), ROI={row.roi_percent:.2f}% "
                    f"(was {old_roi})"
                )

            time.sleep(sleep_s)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=== Backfill summary ==="))
        for k, v in stats.items():
            self.stdout.write(f"  {k}: {v}")

    def _pick_odds(self, odds_list, market_type, predicted):
        """Return (median_value, sample_bookmaker_id, num_bookmakers) or None.

        - `over_under_2.5`: market_id=80, total='2.5', label matches predicted side.
        - `1x2`: market_id=1, label matches predicted side ('home'/'draw'/'away').
        """
        if market_type == "over_under_2.5":
            side = "over" if "over" in predicted else "under"
            side_label = side.capitalize()
            matches = [
                o for o in odds_list
                if o.get("market_id") == 80
                and str(o.get("total") or "").strip() == "2.5"
                and (o.get("label") or "").strip().lower() == side
            ]
        elif market_type == "1x2":
            # 'home' / 'draw' / 'away'
            side = predicted
            if side not in ("home", "draw", "away"):
                return None
            matches = [
                o for o in odds_list
                if o.get("market_id") == 1
                and (o.get("label") or "").strip().lower() == side
            ]
        else:
            # Only over_under_2.5 and 1x2 in the current legacy set; extend later if needed.
            return None

        if not matches:
            return None

        values = []
        bookmakers = []
        for o in matches:
            try:
                v = float(o.get("value") or 0)
            except (TypeError, ValueError):
                continue
            # Reasonable range (drop obvious outliers / suspended lines)
            if 1.05 <= v <= 15.0:
                values.append(v)
                bookmakers.append(o.get("bookmaker_id"))

        if not values:
            return None

        median = statistics.median(values)
        # Return the bookmaker id of the median value if exact match, else first.
        return median, (bookmakers[0] if bookmakers else None), len(values)
