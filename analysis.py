import math
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.feature_extraction.text import TfidfVectorizer

from config import SETTINGS


BULLISH_WORDS = {
    "buy", "bullish", "breakout", "rally", "upside", "long", "support", "green",
    "recover", "strong", "positive", "bounce", "target", "call", "momentum",
}

BEARISH_WORDS = {
    "sell", "bearish", "breakdown", "fall", "downside", "short", "resistance",
    "red", "weak", "negative", "crash", "panic", "put", "loss", "volatile",
}


def build_signals(tweets: pd.DataFrame, interval: str = "15min") -> tuple[pd.DataFrame, pd.DataFrame]:
    if tweets.empty:
        return tweets, pd.DataFrame()

    scored = tweets.copy()
    scored["lexicon_score"] = scored["content"].map(score_market_text)
    scored["engagement_score"] = np.log1p(
        scored["reply_count"] + scored["repost_count"] * 2 + scored["like_count"] + scored["view_count"] * 0.02
    )

    tfidf_signal = build_tfidf_signal(scored["content"].tolist())
    scored["tfidf_signal"] = tfidf_signal
    scored["tweet_signal"] = (
        0.55 * scored["lexicon_score"]
        + 0.30 * scored["tfidf_signal"]
        + 0.15 * np.tanh(scored["engagement_score"] / 5)
    )

    grouped = scored.set_index("timestamp").groupby(pd.Grouper(freq=interval))
    signals = grouped.agg(
        tweet_count=("tweet_id", "count"),
        avg_signal=("tweet_signal", "mean"),
        avg_lexicon=("lexicon_score", "mean"),
        avg_tfidf=("tfidf_signal", "mean"),
        engagement=("engagement_score", "sum"),
    ).dropna(subset=["avg_signal"])

    signals["confidence"] = grouped["tweet_signal"].apply(confidence_interval_width).reindex(signals.index)
    signals["composite_signal"] = np.tanh(signals["avg_signal"] * np.log1p(signals["tweet_count"]))
    signals = signals.reset_index()

    logger.info("Built {} signal rows", len(signals))
    return scored, signals


def score_market_text(text: str) -> float:
    words = {word.strip("#@.,:;!?()[]{}'\"").lower() for word in str(text).split()}
    bullish = len(words & BULLISH_WORDS)
    bearish = len(words & BEARISH_WORDS)
    total = bullish + bearish
    if total == 0:
        return 0.0
    return (bullish - bearish) / total


def build_tfidf_signal(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.array([])

    vectorizer = TfidfVectorizer(max_features=500, min_df=1, ngram_range=(1, 2), lowercase=True)
    matrix = vectorizer.fit_transform(texts)
    feature_names = np.array(vectorizer.get_feature_names_out())

    bullish_columns = np.array([any(word in name for word in BULLISH_WORDS) for name in feature_names])
    bearish_columns = np.array([any(word in name for word in BEARISH_WORDS) for name in feature_names])

    bullish_score = np.asarray(matrix[:, bullish_columns].sum(axis=1)).ravel() if bullish_columns.any() else 0
    bearish_score = np.asarray(matrix[:, bearish_columns].sum(axis=1)).ravel() if bearish_columns.any() else 0
    return np.tanh(bullish_score - bearish_score)


def confidence_interval_width(values: pd.Series) -> float:
    values = values.dropna()
    if len(values) < 2:
        return 0.0
    standard_error = values.std(ddof=1) / math.sqrt(len(values))
    return float(1.96 * standard_error)


def save_signals(signals: pd.DataFrame) -> Path:
    SETTINGS.signal_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        signals.to_csv(SETTINGS.signal_file, index=False)
        output_path = SETTINGS.signal_file
    except PermissionError:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = SETTINGS.signal_file.with_name(f"trading_signals_{timestamp}.csv")
        signals.to_csv(output_path, index=False)
        logger.warning("{} was open or locked, so signals were saved to {}", SETTINGS.signal_file, output_path)

    logger.info("Saved trading signals to {}", output_path)
    return output_path
