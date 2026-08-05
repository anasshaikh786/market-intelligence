import random
import re
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import pandas as pd
from loguru import logger
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as expected
from selenium.webdriver.support.ui import WebDriverWait

from config import SETTINGS


class TwitterScraper:
    """Collects public X/Twitter search results with Selenium and manual login."""

    def __init__(self, settings=SETTINGS):
        self.settings = settings
        self.driver: webdriver.Chrome | None = None
        self.wait: WebDriverWait | None = None
        self.seen_ids: set[str] = set()

    def scrape(self) -> pd.DataFrame:
        self._start_browser()
        tweets: list[dict] = []

        try:
            self._manual_login()
            for hashtag in self.settings.hashtags:
                if len(tweets) >= self.settings.max_tweets:
                    break
                logger.info("Collecting hashtag={}", hashtag)
                try:
                    tweets.extend(self._scrape_hashtag(hashtag, self.settings.max_tweets - len(tweets)))
                except TimeoutException as exc:
                    logger.warning("Skipping {} after search failed: {}", hashtag, exc)
        finally:
            if self.driver:
                self.driver.quit()

        return pd.DataFrame(tweets)

    def _start_browser(self) -> None:
        options = Options()
        if self.settings.headless:
            options.add_argument("--headless=new")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 30)

    def _manual_login(self) -> None:
        assert self.driver is not None
        assert self.wait is not None
        self.driver.get("https://x.com/login")
        print("\nLogin to X in the Chrome window.")
        print("Finish all X onboarding screens until you can see the normal Home page.")

        while True:
            input("Press ENTER after X Home is visible: ")
            current_url = self.driver.current_url.lower()
            if "/login" in current_url or "/signup" in current_url or "/onboarding" in current_url:
                print("X is still showing login/signup/onboarding. Finish that screen first, then press ENTER again.")
                continue

            try:
                self.wait.until(
                    expected.presence_of_element_located(
                        (By.XPATH, '//a[@data-testid="AppTabBar_Home_Link"] | //a[@href="/home"]')
                    )
                )
                return
            except TimeoutException:
                print("I could not confirm the Home page yet. Open x.com/home in this browser, then press ENTER again.")

    def _scrape_hashtag(self, hashtag: str, remaining: int) -> list[dict]:
        assert self.driver is not None
        assert self.wait is not None

        since = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%d")
        query = f"{hashtag} since:{since} -filter:replies"
        self._open_latest_search(query)

        collected: list[dict] = []
        last_height = 0
        idle_scrolls = 0

        for _ in range(self.settings.max_scrolls_per_hashtag):
            cards = self.driver.find_elements(By.XPATH, '//article[@data-testid="tweet"]')
            for card in cards:
                tweet = self._parse_tweet_card(card, hashtag)
                if not tweet or tweet["tweet_id"] in self.seen_ids:
                    continue
                self.seen_ids.add(tweet["tweet_id"])
                collected.append(tweet)
                if len(collected) >= remaining:
                    return collected

            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(self._pause())

            new_height = self.driver.execute_script("return document.body.scrollHeight;")
            idle_scrolls = idle_scrolls + 1 if new_height == last_height else 0
            last_height = new_height
            if idle_scrolls >= 8:
                break

        return collected

    def _open_latest_search(self, query: str) -> None:
        assert self.driver is not None
        assert self.wait is not None

        encoded_query = quote_plus(query)
        urls = [
            f"https://x.com/search?q={encoded_query}&src=typed_query&f=live",
            f"https://twitter.com/search?q={encoded_query}&src=typed_query&f=live",
        ]

        for url in urls:
            if self._load_search_results(url):
                return

        raise TimeoutException("Could not load tweet results after retries")

    def _load_search_results(self, url: str) -> bool:
        assert self.driver is not None
        assert self.wait is not None

        for attempt in range(3):
            self.driver.get(url)
            time.sleep(self._pause())
            self._click_try_again_if_visible()

            try:
                self.wait.until(expected.presence_of_element_located((By.XPATH, '//article[@data-testid="tweet"]')))
                time.sleep(self._pause())
                return True
            except TimeoutException:
                logger.warning("Search result attempt {} failed for {}", attempt + 1, url)
                self.driver.refresh()
                time.sleep(self._pause())

        return False

    def _click_try_again_if_visible(self) -> None:
        assert self.driver is not None

        buttons = self.driver.find_elements(By.XPATH, '//span[text()="Try again"]/ancestor::*[@role="button"]')
        if buttons:
            logger.info("X showed a temporary error; clicking Try again")
            buttons[0].click()
            time.sleep(self._pause())

    def _parse_tweet_card(self, card, source_hashtag: str) -> dict | None:
        try:
            content_parts = [item.text for item in card.find_elements(By.XPATH, './/div[@data-testid="tweetText"]')]
            content = " ".join(part for part in content_parts if part).strip()
            time_node = card.find_element(By.XPATH, ".//time")
            username = self._extract_username(card.text)
            timestamp = time_node.get_attribute("datetime")
            link = self._find_status_link(card)

            if not content or not timestamp or not link:
                return None

            return {
                "tweet_id": link.rsplit("/", 1)[-1],
                "username": username,
                "timestamp": timestamp,
                "content": content,
                "reply_count": self._metric(card, "reply"),
                "repost_count": self._metric(card, "retweet"),
                "like_count": self._metric(card, "like"),
                "view_count": self._metric(card, "analytics"),
                "mentions": self._find_mentions(content),
                "hashtags": self._find_hashtags(content),
                "source_hashtag": source_hashtag,
                "url": link,
                "collected_at": datetime.now(timezone.utc).isoformat(),
            }
        except (WebDriverException, ValueError) as exc:
            logger.debug("Skipped one tweet card: {}", exc)
            return None

    @staticmethod
    def _extract_username(text: str) -> str:
        match = re.search(r"@\w+", text)
        return match.group(0) if match else ""

    @staticmethod
    def _find_status_link(card) -> str:
        links = card.find_elements(By.XPATH, './/a[contains(@href, "/status/")]')
        for link in links:
            href = link.get_attribute("href")
            if href:
                return href
        return ""

    @staticmethod
    def _find_mentions(text: str) -> list[str]:
        return sorted(set(re.findall(r"@\w+", text)))

    @staticmethod
    def _find_hashtags(text: str) -> list[str]:
        return sorted(set(re.findall(r"#\w+", text, flags=re.UNICODE)))

    @staticmethod
    def _metric(card, test_id_part: str) -> int:
        nodes = card.find_elements(By.XPATH, f'.//*[@data-testid="{test_id_part}"]')
        if not nodes:
            return 0
        label = nodes[0].get_attribute("aria-label") or nodes[0].text or ""
        match = re.search(r"([\d,.]+)\s*([KMB]?)", label, flags=re.IGNORECASE)
        if not match:
            return 0
        number = float(match.group(1).replace(",", ""))
        suffix = match.group(2).upper()
        multiplier = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(suffix, 1)
        return int(number * multiplier)

    def _pause(self) -> float:
        return random.uniform(self.settings.request_pause_min, self.settings.request_pause_max)


def save_raw_tweets(tweets: pd.DataFrame) -> None:
    SETTINGS.raw_file.parent.mkdir(parents=True, exist_ok=True)
    tweets.to_parquet(SETTINGS.raw_file, index=False)
    logger.info("Saved {} raw tweets to {}", len(tweets), SETTINGS.raw_file)
