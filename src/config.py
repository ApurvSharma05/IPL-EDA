"""Central configuration, constants, and entity mappings for IPL-EDA."""

from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUTS_DIR = BASE_DIR / "outputs"
NOTEBOOKS_DIR = BASE_DIR / "notebooks"

DATA_DIR.mkdir(exist_ok=True, parents=True)
OUTPUTS_DIR.mkdir(exist_ok=True, parents=True)

RAW_DATA_PATH = DATA_DIR / "IPL.csv"
CLEANED_DATA_PATH = DATA_DIR / "ipl_cleaned_data.csv"
SUMMARY_STATS_PATH = DATA_DIR / "summary_statistics.csv"
SAMPLE_DATA_PATH = DATA_DIR / "sample_deliveries.csv"

# Kaggle dataset coordinates
KAGGLE_DATASET_SLUG = "chaitu20/ipl-dataset2008-2025"

# Franchise Name Standardization Mapping
# Maps historical, rebranded, or spelling variants to unified franchise names
TEAM_NAME_MAPPING = {
    "Delhi Daredevils": "Delhi Capitals",
    "Kings XI Punjab": "Punjab Kings",
    "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
    "Rising Pune Supergiants": "Rising Pune Supergiant",
    "Pune Warriors": "Pune Warriors India",
    "Deccan Chargers": "Sunrisers Hyderabad",
}

# Franchise Official Color Schemes for consistent visualizations
IPL_COLORS = {
    "Mumbai Indians": "#004BA0",
    "Chennai Super Kings": "#FFFF00",
    "Kolkata Knight Riders": "#3A225D",
    "Royal Challengers Bengaluru": "#EC1C24",
    "Royal Challengers Bangalore": "#EC1C24",
    "Rajasthan Royals": "#FF69B4",
    "Sunrisers Hyderabad": "#FF822A",
    "Punjab Kings": "#DD1F2D",
    "Kings XI Punjab": "#DD1F2D",
    "Delhi Capitals": "#004C93",
    "Delhi Daredevils": "#004C93",
    "Gujarat Titans": "#1C1C1C",
    "Lucknow Super Giants": "#00AEEF",
    "Deccan Chargers": "#4253A3",
    "Gujarat Lions": "#F47920",
    "Pune Warriors India": "#2B4593",
    "Rising Pune Supergiant": "#6A1B9A",
    "Kochi Tuskers Kerala": "#800080",
    "Unknown": "#808080",
}

# Over Phase Definitions (0-indexed over numbers: 0..19)
# PowerPlay: 0..5 (Overs 1-6)
# Middle: 6..14 (Overs 7-15)
# Death: 15..19 (Overs 16-20)
PHASE_POWERPLAY = "PowerPlay (1-6)"
PHASE_MIDDLE = "Middle (7-15)"
PHASE_DEATH = "Death (16-20)"
PHASE_ORDER = [PHASE_POWERPLAY, PHASE_MIDDLE, PHASE_DEATH]

# Target Buckets for Chase Analysis
TARGET_LOW = "Low (<130)"
TARGET_MEDIUM = "Medium (130-159)"
TARGET_HIGH = "High (160+)"
TARGET_ORDER = [TARGET_LOW, TARGET_MEDIUM, TARGET_HIGH]

# Analytical Thresholds
MIN_CAREER_RUNS_FILTER = 100
MIN_CAREER_BALLS_FILTER = 60
MIN_BATTER_MATCHES_FILTER = 10
MIN_BOWLER_OVERS_FILTER = 20
MIN_TEAM_MATCHES_CONSISTENCY = 30
