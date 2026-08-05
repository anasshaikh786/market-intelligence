import random
from datetime import datetime, timedelta, timezone

import pandas as pd


SAMPLE_TEXTS = [
    "#nifty50 looks bullish after a clean breakout, watching 24500 target",
    "#banknifty is weak near resistance, short side can work for intraday",
    "#sensex holding support, banks showing positive momentum",
    "Market feels volatile today, wait for confirmation before a fresh buy",
    "#intraday setup: sell below day low, risk management is important",
    "Nifty bounce from support is strong, but do not chase gap up",
    "Bank stocks are red, downside pressure visible in options data",
    "#sensex recovery is positive, breadth improving slowly",
    "Call writers covering positions, bullish momentum in #nifty50",
    "Put side active in #banknifty, range can stay volatile",
    "आज बाजार में momentum strong है #nifty50",
    "बैंक निफ्टी में resistance के पास weakness दिख रही है #banknifty",
]

USERS = ["@marketwatch_in", "@trader_raj", "@nifty_notes", "@dalalstreet_view", "@optiondesk"]


def build_sample_tweets(rows: int) -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    records = []

    for index in range(rows):
        price_level = random.randint(19000, 25000)
        content = f"{random.choice(SAMPLE_TEXTS)} level {price_level} note {index}"
        timestamp = now - timedelta(minutes=random.randint(0, 24 * 60))
        records.append(
            {
                "tweet_id": f"sample_{index}",
                "username": random.choice(USERS),
                "timestamp": timestamp.isoformat(),
                "content": content,
                "reply_count": random.randint(0, 30),
                "repost_count": random.randint(0, 80),
                "like_count": random.randint(0, 400),
                "view_count": random.randint(50, 20_000),
                "mentions": [],
                "hashtags": [word for word in content.split() if word.startswith("#")],
                "source_hashtag": random.choice(["#nifty50", "#sensex", "#banknifty", "#intraday"]),
                "url": f"https://x.com/sample/status/{index}",
                "collected_at": now.isoformat(),
            }
        )

    return pd.DataFrame(records)
