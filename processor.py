import hashlib
import re
import unicodedata

import pandas as pd
from loguru import logger

from config import SETTINGS


URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
SPACE_PATTERN = re.compile(r"\s+")
HASHTAG_PATTERN = re.compile(r"#\w+", flags=re.UNICODE)
MENTION_PATTERN = re.compile(r"@\w+")


def clean_tweets(raw_tweets: pd.DataFrame) -> pd.DataFrame:
    if raw_tweets.empty:
        return raw_tweets

    tweets = raw_tweets.copy()
    tweets["content"] = tweets["content"].fillna("").map(normalize_text)
    tweets["timestamp"] = pd.to_datetime(tweets["timestamp"], utc=True, errors="coerce")
    tweets["collected_at"] = pd.to_datetime(tweets["collected_at"], utc=True, errors="coerce")

    tweets = tweets[tweets["content"].str.len() > 0]
    tweets = tweets[tweets["timestamp"].notna()]

    tweets["text_hash"] = tweets["content"].map(make_text_hash)
    tweets["mentions"] = tweets["content"].map(lambda text: sorted(set(MENTION_PATTERN.findall(text))))
    tweets["hashtags"] = tweets["content"].map(lambda text: sorted(set(HASHTAG_PATTERN.findall(text))))

    metric_columns = ["reply_count", "repost_count", "like_count", "view_count"]
    for column in metric_columns:
        tweets[column] = pd.to_numeric(tweets.get(column, 0), errors="coerce").fillna(0).astype("int32")

    tweets = tweets.drop_duplicates(subset=["tweet_id"], keep="first")
    tweets = tweets.drop_duplicates(subset=["text_hash"], keep="first")
    tweets = tweets.sort_values("timestamp").reset_index(drop=True)

    logger.info("Cleaned tweets: raw={} clean={}", len(raw_tweets), len(tweets))
    return tweets


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text))
    text = URL_PATTERN.sub("", text)
    text = SPACE_PATTERN.sub(" ", text)
    return text.strip()


def make_text_hash(text: str) -> str:
    normalized = normalize_text(text).lower()
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


def save_clean_tweets(tweets: pd.DataFrame) -> None:
    SETTINGS.clean_file.parent.mkdir(parents=True, exist_ok=True)
    tweets.to_parquet(SETTINGS.clean_file, index=False)
    logger.info("Saved {} clean tweets to {}", len(tweets), SETTINGS.clean_file)
