"""Automated Command Line Pipeline for IPL Data Ingestion, Cleaning, and Validation."""

import argparse
import logging
import sys
from pathlib import Path
import pandas as pd

# Configure UTF-8 encoding safely on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.config import CLEANED_DATA_PATH, DATA_DIR, SUMMARY_STATS_PATH
from src.data_cleaning import run_pipeline
from src.metrics import generate_summary_statistics_df
from src.validation import run_evaluation_suite, validate_deliveries_dataframe

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("IPL-Pipeline")


def main():
    parser = argparse.ArgumentParser(
        description="IPL Telemetry ETL, Validation, and Metric Pipeline"
    )
    parser.add_argument(
        "--raw-path",
        type=str,
        default=None,
        help="Optional custom path to raw IPL CSV file",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip Pandera schema validation",
    )
    parser.add_argument(
        "--skip-evaluation",
        action="store_true",
        help="Skip Golden Benchmark evaluation suite",
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("[START] IPL DATA ENGINEERING PIPELINE")
    logger.info("=" * 70)

    # 1. Clean and engineer features
    cleaned_df = run_pipeline(raw_path=args.raw_path, export_cleaned=True)
    logger.info(f"[OK] Preprocessing complete: {len(cleaned_df):,} deliveries processed.")

    # 2. Schema Validation
    if not args.skip_validation:
        logger.info("\nRunning Pandera Schema Validation Contract...")
        validate_deliveries_dataframe(cleaned_df)
        logger.info("[OK] Schema Contract Verified: 100% compliant.")

    # 3. Golden Evaluation Suite
    if not args.skip_evaluation:
        logger.info("\nRunning Golden Tournament Benchmark Tests...")
        eval_report = run_evaluation_suite(cleaned_df)
        for check, result in eval_report.items():
            logger.info(f"  * {check}: {result}")
        if eval_report["status"] != "ALL_CHECKS_PASSED":
            logger.warning("[WARNING] Some evaluation checks raised warnings.")
        else:
            logger.info("[OK] All Benchmark Checks Passed.")

    # 4. Generate and Export Summary Statistics
    logger.info("\nCompiling Tournament Summary KPIs...")
    summary_df = generate_summary_statistics_df(cleaned_df)
    SUMMARY_STATS_PATH.parent.mkdir(exist_ok=True, parents=True)
    summary_df.to_csv(SUMMARY_STATS_PATH, index=False)
    logger.info(f"[OK] Summary statistics saved to: {SUMMARY_STATS_PATH}")

    print("\n" + "=" * 70)
    print("TOURNAMENT EXECUTIVE SUMMARY")
    print("=" * 70)
    for _, row in summary_df.iterrows():
        print(f"  {row['Metric']:<35} : {row['Value']}")
    print("=" * 70)
    logger.info("[DONE] Pipeline executed successfully!")


if __name__ == "__main__":
    main()
