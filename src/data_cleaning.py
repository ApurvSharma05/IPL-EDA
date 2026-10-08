"""Data ingestion, normalization, and feature engineering pipeline for IPL telemetry."""

import logging
from pathlib import Path
from typing import Optional, Union
import numpy as np
import pandas as pd

from src.config import (
    CLEANED_DATA_PATH,
    DATA_DIR,
    KAGGLE_DATASET_SLUG,
    PHASE_DEATH,
    PHASE_MIDDLE,
    PHASE_ORDER,
    PHASE_POWERPLAY,
    RAW_DATA_PATH,
    SAMPLE_DATA_PATH,
    TEAM_NAME_MAPPING,
)

logger = logging.getLogger(__name__)


def assign_over_phase(over_num: int) -> str:
    """Classify 0-based over number into PowerPlay, Middle, or Death phase.

    0-5   -> PowerPlay (Overs 1-6)
    6-14  -> Middle (Overs 7-15)
    15-19 -> Death (Overs 16-20)
    """
    if over_num < 6:
        return PHASE_POWERPLAY
    if over_num < 15:
        return PHASE_MIDDLE
    return PHASE_DEATH


def resolve_raw_csv_path(custom_path: Optional[Union[str, Path]] = None) -> Path:
    """Finds raw IPL CSV from custom path, local cache, or KaggleHub."""
    if custom_path and Path(custom_path).exists():
        return Path(custom_path)

    if RAW_DATA_PATH.exists():
        return RAW_DATA_PATH

    # Check KaggleHub cache
    try:
        import kagglehub

        logger.info(f"Checking / downloading dataset via kagglehub: {KAGGLE_DATASET_SLUG}")
        cache_dir = Path(kagglehub.dataset_download(KAGGLE_DATASET_SLUG))
        csv_files = sorted(cache_dir.glob("*.csv"))
        if csv_files:
            preferred = next((f for f in csv_files if "ipl" in f.name.lower()), csv_files[0])
            logger.info(f"Located KaggleHub file: {preferred}")
            return preferred
    except Exception as exc:
        logger.warning(f"KaggleHub retrieval failed or offline: {exc}")

    # Fallback to sample data if exists
    if SAMPLE_DATA_PATH.exists():
        logger.info(f"Using sample dataset fallback: {SAMPLE_DATA_PATH}")
        return SAMPLE_DATA_PATH

    raise FileNotFoundError(
        "No IPL CSV found. Provide a path or ensure KaggleHub/internet connection is available."
    )


def load_raw_dataset(csv_path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    """Loads raw deliveries CSV with safe low_memory options."""
    path = resolve_raw_csv_path(csv_path)
    logger.info(f"Loading raw dataset from: {path}")
    df = pd.read_csv(path, low_memory=False)
    logger.info(f"Loaded {len(df):,} deliveries, {len(df.columns)} columns.")
    return df


def clean_ipl_telemetry(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Cleans, normalizes, and engineers domain features on IPL ball telemetry.

    Key guarantees:
    1. Unified entity names across batting_team, bowling_team, match_won_by, toss_winner.
    2. Accurate integer season extraction (handling '2007/08' dirty season strings).
    3. Proper datetime parsing.
    4. Cricket-compliant bowler runs conceded (excludes byes/leg-byes).
    5. Phase segmentation (PowerPlay, Middle, Death).
    """
    df = raw_df.copy()

    # 1. Standardize Franchise Names across all relevant columns
    for col in ["batting_team", "bowling_team", "match_won_by", "toss_winner"]:
        if col in df.columns:
            df[col] = df[col].replace(TEAM_NAME_MAPPING)

    # Alias winning_team for backward compatibility
    if "winning_team" not in df.columns and "match_won_by" in df.columns:
        df["winning_team"] = df["match_won_by"]

    # 2. Datetime and Season Standardization
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    if "season" in df.columns:
        # Extract 4-digit year as integer to normalize formats like '2007/08', '2008'
        extracted_year = df["season"].astype(str).str.extract(r"(\d{4})")[0]
        df["season_year"] = pd.to_numeric(extracted_year, errors="coerce").fillna(0).astype(int)
    else:
        df["season_year"] = df["date"].dt.year if "date" in df.columns else 0

    # 3. Deduplication check
    df = df.drop_duplicates()

    # 4. Harmonize Column Aliases (handling variations like runs_off_bat vs runs_batter)
    if "runs" not in df.columns:
        if "runs_batter" in df.columns:
            df["runs"] = df["runs_batter"]
        elif "runs_off_bat" in df.columns:
            df["runs"] = df["runs_off_bat"]
        else:
            df["runs"] = 0

    if "extras" not in df.columns:
        if "runs_extras" in df.columns:
            df["extras"] = df["runs_extras"]
        else:
            df["extras"] = 0

    if "wickets" not in df.columns:
        if "bowler_wicket" in df.columns:
            df["wickets"] = df["bowler_wicket"]
        elif "is_wicket" in df.columns:
            df["wickets"] = df["is_wicket"]
        else:
            df["wickets"] = 0

    # 5. Core Feature Engineering
    # Total runs in the delivery (bat runs + extras)
    df["runs_total"] = df["runs"] + df["extras"]

    # Accurate bowler runs conceded (Cricket Rule: byes and leg-byes are NOT debited to bowler)
    if "runs_bowler" in df.columns:
        df["runs_conceded_bowler"] = df["runs_bowler"]
    elif "extra_type" in df.columns:
        is_fielding_extra = df["extra_type"].isin(["byes", "legbyes"])
        df["runs_conceded_bowler"] = np.where(is_fielding_extra, 0, df["runs_total"])
    else:
        df["runs_conceded_bowler"] = df["runs_total"]

    # Binary wicket indicator
    df["is_wicket"] = (df["wickets"] > 0).astype(int)

    # Over phase categorization (0-indexed over)
    if "over" in df.columns:
        df["phase"] = df["over"].apply(assign_over_phase)
        df["phase"] = pd.Categorical(df["phase"], categories=PHASE_ORDER, ordered=True)

    # 6. Categorical Missing Value Imputation
    if "player_dismissed" not in df.columns:
        df["player_dismissed"] = df["player_out"] if "player_out" in df.columns else np.nan
    df["player_dismissed"] = df["player_dismissed"].fillna("Not Out")

    if "dismissal_kind" not in df.columns:
        df["dismissal_kind"] = df["wicket_kind"] if "wicket_kind" in df.columns else np.nan
    df["dismissal_kind"] = df["dismissal_kind"].fillna("Not Applicable")

    if "fielder" not in df.columns:
        df["fielder"] = df["fielders"] if "fielders" in df.columns else np.nan
    df["fielder"] = df["fielder"].fillna("N/A")

    logger.info(f"Cleaning complete. Output shape: {df.shape[0]:,} rows x {df.shape[1]} columns.")
    return df


def run_pipeline(
    raw_path: Optional[Union[str, Path]] = None,
    export_cleaned: bool = True,
    create_sample: bool = True,
) -> pd.DataFrame:
    """Executes the complete data ingestion and cleaning pipeline."""
    raw_df = load_raw_dataset(raw_path)
    cleaned_df = clean_ipl_telemetry(raw_df)

    if export_cleaned:
        DATA_DIR.mkdir(exist_ok=True, parents=True)
        cleaned_df.to_csv(CLEANED_DATA_PATH, index=False)
        logger.info(f"Cleaned dataset exported to: {CLEANED_DATA_PATH}")

    if create_sample and not SAMPLE_DATA_PATH.exists():
        # Export a 20-match sample for fast unit tests and offline testing
        sample_matches = cleaned_df["match_id"].drop_duplicates().head(20)
        sample_df = cleaned_df[cleaned_df["match_id"].isin(sample_matches)]
        sample_df.to_csv(SAMPLE_DATA_PATH, index=False)
        logger.info(f"Sample dataset exported to: {SAMPLE_DATA_PATH}")

    return cleaned_df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_pipeline()
