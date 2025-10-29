#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
from typing import List

import pandas as pd
import matplotlib

# Use non-interactive backend for headless environments
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def find_portfolio_value_files(input_dir: Path) -> List[Path]:
    csv_files = sorted(input_dir.glob("*_*portfolio_values.csv"))  # broad match
    # Also include direct pattern just in case
    csv_files.extend([p for p in input_dir.glob("*_portfolio_values.csv") if p not in csv_files])
    # De-duplicate while preserving order
    seen = set()
    unique_files = []
    for p in csv_files:
        if p.name not in seen and p.is_file():
            seen.add(p.name)
            unique_files.append(p)
    return unique_files


def make_title_from_filename(path: Path) -> str:
    name = path.stem  # without .csv
    # Remove common prefixes/suffixes
    name = name.replace("backtest_", "")
    name = name.replace("_portfolio_values", "")
    # Humanize
    return name.replace("_", " ").title()


def plot_equity_curve(csv_path: Path, output_dir: Path) -> Path:
    df = pd.read_csv(csv_path)

    if "portfolio_value" not in df.columns:
        raise ValueError(f"'portfolio_value' column not found in {csv_path}")

    # Coerce numeric portfolio values and drop invalid rows
    df["portfolio_value"] = pd.to_numeric(df["portfolio_value"], errors="coerce")
    df = df.dropna(subset=["portfolio_value"]).copy()

    # Use date if present, otherwise index
    x = None
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])  # drop rows where date failed to parse
        df = df.sort_values("date")
        x = df["date"]
    else:
        df = df.reset_index(drop=False)
        x = df.index

    y = df["portfolio_value"]

    title = make_title_from_filename(csv_path)

    plt.style.use("seaborn-v0_8")
    fig, ax = plt.subplots(figsize=(12, 5), dpi=150)
    ax.plot(x, y, color="#1f77b4", linewidth=1.6)
    ax.set_title(f"{title} — Equity Curve", fontsize=14)
    ax.set_ylabel("Portfolio Value")

    if isinstance(x.iloc[0] if hasattr(x, "iloc") else x, pd.Timestamp):
        ax.set_xlabel("Date")
        for label in ax.get_xticklabels():
            label.set_rotation(45)
            label.set_horizontalalignment("right")
    else:
        ax.set_xlabel("Time")

    ax.grid(True, linestyle=":", linewidth=0.8, alpha=0.7)
    fig.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / (csv_path.stem + ".png")
    fig.savefig(output_path)
    plt.close(fig)
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate equity curve PNGs from backtest portfolio value CSVs."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "results",
        help="Directory containing *_portfolio_values.csv files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "results" / "equity_curves",
        help="Directory to save PNG equity curve images",
    )

    args = parser.parse_args()

    input_dir: Path = args.input_dir
    output_dir: Path = args.output_dir

    if not input_dir.exists() or not input_dir.is_dir():
        raise SystemExit(f"Input directory not found: {input_dir}")

    files = find_portfolio_value_files(input_dir)
    if not files:
        print(f"No portfolio values CSV files found in {input_dir}")
        return

    print(f"Found {len(files)} portfolio value files. Saving to {output_dir}...")

    saved = 0
    for csv_path in files:
        try:
            out_path = plot_equity_curve(csv_path, output_dir)
            print(f"Saved: {out_path}")
            saved += 1
        except Exception as exc:
            print(f"Skipping {csv_path.name}: {exc}")

    print(f"Done. Saved {saved} PNG files to {output_dir}")


if __name__ == "__main__":
    main()
