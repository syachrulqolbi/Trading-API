from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from trading_api.service import MarketService
from trading_api.settings import JOBS, AppSettings

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh trading market data and optionally export Excel files.")
    parser.add_argument(
        "--job",
        choices=["all", *JOBS.keys()],
        default="all",
        help="Which sheet job to refresh. Default: all.",
    )
    parser.add_argument(
        "--excel",
        action="store_true",
        help="Also write Excel output files to EXPORT_OUTPUT_DIR / outputs.",
    )
    parser.add_argument(
        "--json-out",
        default=None,
        help="Optional JSON file path for the API payload.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    service = MarketService(AppSettings())
    job_names = None if args.job == "all" else [args.job]
    payload = service.refresh(export_excel=args.excel, job_names=job_names)

    if args.json_out:
        output_path = Path(args.json_out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({key: payload.get(key) for key in ["status", "updated_at", "counts", "excel_files", "errors"] if key in payload}, indent=2))


if __name__ == "__main__":
    main()
