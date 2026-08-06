# Real-Time Market Intelligence from Indian Stock Tweets

This project collects public X/Twitter posts related to Indian stock market discussions and converts the text into quantitative signals that can be used for market sentiment research.

The scraper uses Selenium browser automation only. It does not use the Twitter/X API or any paid API.

## Features

- Targets up to 2,000 recent X/Twitter posts per hashtag for `#nifty50`, `#sensex`, `#banknifty`, and `#intraday`
- Extracts username, timestamp, tweet content, engagement metrics, mentions, hashtags, source hashtag, URL, and collection time
- Handles manual login, retry flow, temporary X errors, and randomized pauses
- Cleans and normalizes text while preserving Indian language Unicode content
- Deduplicates tweets using tweet ids and stable text hashes
- Stores raw and cleaned data in Parquet format
- Converts tweet text into numeric signals using TF-IDF and a market sentiment lexicon
- Aggregates tweet signals into 15-minute market sentiment windows
- Generates a low-memory sampled visualization

## Project Structure

```text
.
|-- main.py                         # CLI entry point
|-- scraper.py                      # Selenium-based X/Twitter scraper
|-- processor.py                    # cleaning, normalization, deduplication
|-- analysis.py                     # TF-IDF, lexicon scoring, signal aggregation
|-- visualization.py                # memory-friendly plotting
|-- sample_data.py                  # local sample data generator
|-- config.py                       # central project settings
|-- requirements.txt                # Python dependencies
|-- docs/
|   `-- TECHNICAL_DOCUMENTATION.md  # approach, data structures, complexity
|-- data/
|   |-- raw_tweets.parquet          # sample/raw collected data
|   `-- clean_tweets.parquet        # cleaned sample output
|-- output/
|   |-- trading_signals.csv         # signal output
|   |-- signal_plot.png             # signal chart
|   `-- summary.txt                 # short analysis summary
`-- logs/                           # runtime logs, ignored by Git
```

## Environment Setup

Use Python 3.11 or newer. The project was tested in a Windows virtual environment.

```powershell
cd "C:\Anas\Qode company project\market-intelligence"
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Google Chrome must be installed. Selenium Manager will automatically handle ChromeDriver for recent Selenium versions.

## Run with Sample Data

Use this command to test the full pipeline without scraping X:

```powershell
python main.py pipeline --sample --rows 300
```

This creates:

```text
data/raw_tweets.parquet
data/clean_tweets.parquet
output/trading_signals.csv
output/signal_plot.png
output/summary.txt
```

Existing output files are overwritten on each run. If `output/trading_signals.csv` is open in Excel or another app, the code saves a timestamped CSV copy instead of crashing.

## Run Real X/Twitter Collection

```powershell
python main.py pipeline
```

Steps:

1. Chrome opens automatically.
2. Log in to X manually.
3. Finish all onboarding screens until the normal X Home page is visible.
4. Return to the terminal and press ENTER.
5. The scraper searches each hashtag and targets up to 2,000 tweets per hashtag.

You can also run each step separately:

```powershell
python main.py collect
python main.py process
python main.py analyze
```

## Current Output

The latest X/Twitter collection run targeted up to 2,000 tweets per hashtag. X rate-limited the browser session during collection, so the actual dataset contains the tweets that X returned before limiting the searches.

```text
Raw tweets: 521
Clean tweets: 516
Signal windows: 90
Latest signal: 0.0435 bullish
```

Raw tweets by source hashtag:

```text
#nifty50      248
#sensex       210
#intraday      58
#banknifty      5
```

Top hashtags from the run included:

```text
#Nifty50
#Sensex
#sensex
#Nifty
#nifty
```

## Output Files

- `data/raw_tweets.parquet`: raw scraped tweets
- `data/clean_tweets.parquet`: cleaned and deduplicated tweets
- `output/trading_signals.csv`: 15-minute aggregated signal table
- `output/signal_plot.png`: sampled plot of composite signal over time
- `output/summary.txt`: quick readable summary
- `logs/app.log`: runtime logs

`output/trading_signals.csv` columns:

- `timestamp`: signal window timestamp
- `tweet_count`: number of tweets in the window
- `avg_signal`: average tweet-level signal
- `avg_lexicon`: bullish/bearish keyword score
- `avg_tfidf`: TF-IDF weighted signal
- `engagement`: weighted engagement score
- `confidence`: 95 percent confidence interval width
- `composite_signal`: final signal, approximately between `-1` and `1`

## Data Structures Used

- `set`: tracks seen tweet ids during scraping for O(1) duplicate checks
- `list[dict]`: stores scraped tweet records before converting to a dataframe
- `pandas.DataFrame`: batch processing, cleaning, aggregation, and storage
- `dict`: maps metric names and suffix multipliers such as `K`, `M`, and `B`
- sparse TF-IDF matrix: memory-efficient text vector representation from scikit-learn
- Parquet columnar storage: efficient disk storage for structured tweet data

## Technical Notes

The final signal combines three simple components:

- Lexicon score: counts bullish and bearish market terms
- TF-IDF score: weights important market words across tweets
- Engagement score: adds influence from likes, reposts, replies, and views

The pipeline is intentionally simple and explainable. It is suitable for a 24-hour assignment while still showing production practices such as logging, error handling, retries, deduplication, clear modules, and documented outputs.

For more technical detail, see [docs/TECHNICAL_DOCUMENTATION.md](docs/TECHNICAL_DOCUMENTATION.md).

## Important Note

X search results can vary by account, time, rate limits, and temporary page errors. The code is configured to target up to 2,000 tweets per hashtag, or about 8,000 total before deduplication, but the actual count depends on what X returns during the run.
When X shows a temporary `Retry` or `Try again` screen, the scraper clicks it and falls back to simpler search queries if needed.
If X rate limits the session or stops returning new tweet cards, the scraper saves the tweets collected so far and the analysis runs on that available dataset.
