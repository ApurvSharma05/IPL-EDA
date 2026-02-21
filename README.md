# IPL Data Analysis - Exploratory Data Analysis

**Author:** Apurv Sharma  
**Objective:** Understand IPL cricket through comprehensive data analysis

---

## 📋 Table of Contents
1. [Overview](#overview)
2. [Project Structure](#project-structure)
3. [Getting Started](#getting-started)
4. [Dataset](#dataset)
5. [Analysis Sections](#analysis-sections)
6. [Key Metrics](#key-metrics)
7. [Troubleshooting](#troubleshooting)

---

## 📊 Overview

A **comprehensive EDA** of IPL ball-by-ball data covering seasons 2008–2025, built to be beginner-friendly, interview-ready, and professionally visualized.

**Highlights:**
- 9 analysis sections
- 20+ annotated visualizations
- Schema-safe code (handles column name variants)
- Exportable cleaned CSV and summary statistics

---

## 🏗️ Project Structure

```
IPL_EDA_Improved.ipynb
├── Section 0 – Setup & Libraries
├── Section 1 – Data Loading & Overview
├── Section 2 – Data Cleaning & Preparation
├── Section 3 – Match Analysis (matches per season)
├── Section 4 – Team Analysis (wins, win %)
├── Section 5 – Batting Analysis (top scorers, strike rate)
├── Section 6 – Bowling Analysis (wickets, economy)
├── Section 7 – Strategic Analysis
│   ├── 7.1 Toss Impact
│   ├── 7.2 Innings Runs Distribution
│   ├── 7.3 Most Active Venues
│   ├── 7.4 Advanced Deep-Dive
│   │   ├── Top 10 Batsmen
│   │   ├── Top 10 Bowlers
│   │   ├── Economy vs Wickets Scatter
│   │   ├── Scoring by Over Phase
│   │   ├── Chase Success Analysis
│   │   ├── Wicket Type Distribution
│   │   ├── Home vs Away Performance
│   │   └── Team Performance Heatmap
├── Section 8 – Cumulative Runs Trend
└── Section 9 – Conclusion & Key Takeaways
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.7+
- Jupyter Notebook / Google Colab

### Installation
```bash
pip install pandas numpy matplotlib seaborn kagglehub
jupyter notebook IPL_EDA_Improved.ipynb
```

### Quick Start
1. Run **Section 0** to load libraries
2. Section 1 auto-downloads the dataset via `kagglehub`
3. Run all cells in sequence

---

## 📥 Dataset

### Source
Downloaded automatically via:
```python
import kagglehub
path = kagglehub.dataset_download("chaitu20/ipl-dataset2008-2025")
```

### Expected Columns

| Column | Description |
|--------|-------------|
| `match_id` | Unique match identifier |
| `season` | IPL season (e.g. `2024`) |
| `date` | Match date |
| `innings` | Innings number (1 or 2) |
| `batting_team` / `bowling_team` | Team names |
| `batter` / `bowler` | Player names |
| `runs_batter` | Runs scored by batsman |
| `runs_extras` | Extra runs |
| `bowler_wicket` | Wicket indicator (0/1) |
| `over` | Over number (0-based) |
| `venue` | Stadium name |
| `toss_winner` | Toss-winning team |
| `match_won_by` | Match-winning team |
| `team_runs` | Team score at that point |

> The notebook handles minor column name variants automatically.

---

## 📈 Analysis Sections

| Section | Question Answered |
|---------|------------------|
| Match Analysis | How many matches per season? |
| Team Wins | Which teams won the most? |
| Win Percentage | Which team is most consistent? |
| Top Scorers | Who scored the most runs? |
| Strike Rate | Who bats most aggressively? |
| Wicket Takers | Who took the most wickets? |
| Economy Rate | Who is the most economical bowler? |
| Toss Impact | Does toss affect match outcome? |
| Over Phases | How do scoring rates differ by phase? |
| Chase Analysis | How does target size affect chase success? |
| Dismissal Types | What are the most common dismissals? |
| Home vs Away | Do teams perform better at home? |
| Season Heatmap | How has each team performed per season? |

---

## 🔢 Key Metrics

```
Win %       = (Wins ÷ Matches Played) × 100
Strike Rate = (Runs ÷ Balls Faced) × 100
Economy     = Runs Conceded ÷ (Deliveries ÷ 6)
```

---

## 📤 Outputs

Running the full notebook exports:
- `ipl_cleaned_data.csv` — cleaned ball-by-ball data
- `summary_statistics.csv` — key aggregate metrics

---

## 🔧 Troubleshooting

| Problem | Fix |
|---------|-----|
| Missing module | `pip install pandas numpy matplotlib seaborn kagglehub` |
| No CSV found | Check `kagglehub` download path; rerun Section 1 |
| Column not found | Print `ipl.columns` and verify names |
| Empty plots | Check for missing values with `ipl.isnull().sum()` |
| Small plots | Set `plt.rcParams['figure.figsize'] = (15, 8)` |

---

## 📄 License

Free to use for learning, portfolio demonstration, and interview preparation.

