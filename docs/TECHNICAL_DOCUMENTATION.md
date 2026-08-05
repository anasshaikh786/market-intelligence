# Technical Documentation

## Objective

The goal is to build a practical market intelligence pipeline that collects Indian stock market discussions from X/Twitter and converts text into numerical signals for analysis.

The implementation avoids paid APIs and the official Twitter/X API. Selenium is used because it allows a real browser session with manual login.

## Pipeline Design

The system has four stages:

1. Collection
   - Opens X in Chrome through Selenium
   - Uses manual login to avoid storing credentials
   - Searches hashtags such as `#nifty50`, `#sensex`, `#banknifty`, and `#intraday`
   - Targets up to 2,000 tweets per hashtag before moving to the next hashtag
   - Extracts tweet metadata and engagement metrics
   - Retries temporary X failures such as "Try again"

2. Processing
   - Normalizes Unicode text using NFKC
   - Removes URLs and extra whitespace
   - Extracts mentions and hashtags
   - Converts timestamps and metrics into consistent types
   - Deduplicates tweets by `tweet_id` and `text_hash`

3. Analysis
   - Builds a bullish/bearish lexicon score
   - Builds TF-IDF vectors with a capped feature count
   - Adds a weighted engagement score
   - Aggregates tweet-level scores into 15-minute windows
   - Calculates confidence interval width for each window

4. Visualization
   - Samples data before plotting to keep memory usage low
   - Saves the final chart as `output/signal_plot.png`

## Data Structures Used

| Data structure | Used in | Reason |
| --- | --- | --- |
| `set` | `scraper.py` | O(1) duplicate checks for seen tweet ids |
| `list[dict]` | `scraper.py`, `sample_data.py` | Simple temporary storage for collected tweet records |
| `dict` | `analysis.py`, `scraper.py` | Fast lookup for metric multipliers and scoring weights |
| `pandas.DataFrame` | processing and analysis | Efficient tabular cleaning, grouping, aggregation, and export |
| sparse matrix | TF-IDF vectorization | Memory-efficient text representation |
| Parquet files | `data/` | Efficient columnar storage with good compression |

## Complexity

Let `n` be the number of tweets and `v` be the capped TF-IDF vocabulary size.

| Step | Time complexity | Space complexity |
| --- | --- | --- |
| Scraping dedup check | O(n) average | O(n) for seen ids and records |
| Cleaning | O(n) | O(n) |
| Text hashing | O(total text length) | O(n) |
| TF-IDF | O(n * v) with sparse storage | O(non-zero terms) |
| Signal aggregation | O(n) | O(number of time windows) |
| Plot sampling | O(k), where k is sampled points | O(k) |

The TF-IDF feature count is capped at 500 to keep memory predictable.

## Indian Market Understanding

The hashtags are selected around highly discussed Indian index and intraday trading topics:

- `#nifty50`: NSE Nifty 50 market direction
- `#sensex`: BSE Sensex market sentiment
- `#banknifty`: banking index, often active in options and intraday trading
- `#intraday`: short-term trading setups and market momentum

The lexicon includes market words such as `breakout`, `support`, `resistance`, `rally`, `short`, `put`, `call`, `weak`, and `volatile`. These terms are common in Indian retail trading discussions.

## Handling Technical Constraints

X can show temporary errors, onboarding screens, and rate-limit style behavior. The scraper handles this by:

- using manual login instead of storing credentials
- opening direct search URLs instead of relying on the Explore search box
- retrying failed searches
- clicking visible "Retry" or "Try again" buttons
- falling back from advanced search queries to simpler hashtag searches
- using randomized pauses between actions
- skipping one failed hashtag without losing earlier collected data

## Scalability

For 10x data volume, the current design can be extended by:

- writing scraped tweets in batches instead of only at the end
- processing Parquet partitions by date or hashtag
- increasing TF-IDF `min_df` to reduce vocabulary noise
- running cleaning and scoring per partition
- keeping visualization sampled instead of plotting all rows

The current implementation keeps the code simple while leaving a clear path for scaling.

## Limitations

- X page structure can change, so Selenium selectors may need updates.
- Collected tweet count depends on what X search returns in the active browser session.
- The generated signal is for research and demonstration, not direct trading advice.
