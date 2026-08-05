import argparse
import logging
from pathlib import Path

import pandas as pd
from loguru import logger

from analysis import build_signals, save_signals
from config import SETTINGS
from processor import clean_tweets, save_clean_tweets
from scraper import TwitterScraper, save_raw_tweets
from sample_data import build_sample_tweets
from visualization import plot_signals


def setup_logging() -> None:
    SETTINGS.log_file.parent.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(SETTINGS.log_file, rotation="5 MB", level="INFO")
    logger.add(lambda message: print(message, end=""), level="INFO")
    logging.getLogger("selenium").setLevel(logging.WARNING)


def collect() -> None:
    scraper = TwitterScraper()
    raw_tweets = scraper.scrape()
    save_raw_tweets(raw_tweets)
    print(f"Collected {len(raw_tweets)} tweets -> {SETTINGS.raw_file}")


def make_sample(rows: int) -> None:
    raw_tweets = build_sample_tweets(rows)
    save_raw_tweets(raw_tweets)
    print(f"Created sample data with {rows} rows -> {SETTINGS.raw_file}")


def process() -> pd.DataFrame:
    raw_tweets = read_parquet(SETTINGS.raw_file)
    clean = clean_tweets(raw_tweets)
    save_clean_tweets(clean)
    print(f"Clean rows: {len(clean)} -> {SETTINGS.clean_file}")
    return clean


def analyze() -> None:
    clean = read_parquet(SETTINGS.clean_file)
    scored, signals = build_signals(clean)
    signal_path = save_signals(signals)
    plot_signals(signals)
    write_summary(scored, signals)
    print(f"Signals -> {signal_path}")
    print(f"Plot -> {SETTINGS.plot_file}")
    print(f"Summary -> {SETTINGS.summary_file}")


def run_pipeline(use_sample: bool, sample_rows: int) -> None:
    if use_sample:
        make_sample(sample_rows)
    else:
        collect()
    process()
    analyze()


def read_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}. Run the previous command first.")
    return pd.read_parquet(path)


def write_summary(scored: pd.DataFrame, signals: pd.DataFrame) -> None:
    SETTINGS.summary_file.parent.mkdir(parents=True, exist_ok=True)
    if signals.empty:
        summary = "No signals were created. Check whether the cleaned tweet file has rows."
    else:
        latest = signals.iloc[-1]
        direction = "bullish" if latest["composite_signal"] > 0 else "bearish" if latest["composite_signal"] < 0 else "neutral"
        top_hashtags = scored["hashtags"].explode().value_counts().head(10)
        summary = (
            f"Rows analyzed: {len(scored)}\n"
            f"Signal windows: {len(signals)}\n"
            f"Latest window: {latest['timestamp']}\n"
            f"Latest signal: {latest['composite_signal']:.4f} ({direction})\n"
            f"Confidence width: {latest['confidence']:.4f}\n\n"
            f"Top hashtags:\n{top_hashtags.to_string()}\n"
        )
    SETTINGS.summary_file.write_text(summary, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Indian stock-market Twitter intelligence pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("collect", help="Scrape X/Twitter using Selenium and save raw Parquet")
    subparsers.add_parser("process", help="Clean, normalize, and deduplicate raw tweets")
    subparsers.add_parser("analyze", help="Create text signals and plots from cleaned tweets")

    sample = subparsers.add_parser("sample", help="Create realistic local sample data")
    sample.add_argument("--rows", type=int, default=250, help="Number of sample tweets to create")

    pipeline = subparsers.add_parser("pipeline", help="Run collect/process/analyze or sample/process/analyze")
    pipeline.add_argument("--sample", action="store_true", help="Use local sample data instead of scraping X")
    pipeline.add_argument("--rows", type=int, default=250, help="Rows to create when --sample is used")
    return parser.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()

    if args.command == "collect":
        collect()
    elif args.command == "sample":
        make_sample(args.rows)
    elif args.command == "process":
        process()
    elif args.command == "analyze":
        analyze()
    elif args.command == "pipeline":
        run_pipeline(args.sample, args.rows)


if __name__ == "__main__":
    main()
