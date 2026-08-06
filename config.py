from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    hashtags: tuple[str, ...] = ("#nifty50", "#sensex", "#banknifty", "#intraday")
    max_tweets_per_hashtag: int = 2000
    max_scrolls_per_hashtag: int = 160
    scroll_pause_seconds: float = 2.2
    request_pause_min: float = 1.0
    request_pause_max: float = 3.0
    hashtag_cooldown_seconds: float = 8.0
    rate_limit_cooldown_seconds: float = 90.0
    headless: bool = False
    raw_file: Path = Path("data/raw_tweets.parquet")
    clean_file: Path = Path("data/clean_tweets.parquet")
    signal_file: Path = Path("output/trading_signals.csv")
    summary_file: Path = Path("output/summary.txt")
    plot_file: Path = Path("output/signal_plot.png")
    log_file: Path = Path("logs/app.log")


SETTINGS = Settings()
