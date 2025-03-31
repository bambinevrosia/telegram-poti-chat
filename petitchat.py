import requests
from telegram import Bot
from telegram.error import TelegramError
import asyncio
import os 
import json
from typing import Dict, List, Set
from dotenv import load_dotenv

load_dotenv()
# Configuration
WAIT_TIME = 10  # minutes between checks
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
# Dictionary mapping channel IDs to their subreddits
CHANNELS = {
    -4723752995: [  # Cat channel
        "https://www.reddit.com/r/cat/.json",
        "https://www.reddit.com/r/kittens/top/.json",
        "https://www.reddit.com/r/istanbulcats/top/.json"
    ],
    -1001234567890: [  # Example second channel
        "https://www.reddit.com/r/dogs/.json",
        "https://www.reddit.com/r/puppies/top/.json"
    ]
}

bot = Bot(token=TELEGRAM_TOKEN)

# File to store sent photos per channel
SENT_PHOTOS_FILE = "sent_photos.json"

def load_sent_photos() -> Dict[int, Set[str]]:
    """Loads sent photos from file, organized by channel ID."""
    try:
        with open(SENT_PHOTOS_FILE, "r") as f:
            data = json.load(f)
            # Convert lists back to sets
            return {int(channel_id): set(photos) for channel_id, photos in data.items()}
    except (FileNotFoundError, json.JSONDecodeError):
        return {channel_id: set() for channel_id in CHANNELS}

def save_sent_photos(sent_photos: Dict[int, Set[str]]):
    """Saves sent photos to file, converting sets to lists for JSON serialization."""
    with open(SENT_PHOTOS_FILE, "w") as f:
        # Convert sets to lists for JSON serialization
        print(sent_photos)
        data = {channel_id: list(photos) for channel_id, photos in sent_photos.items()}
        json.dump(data, f)

def get_new_photo(subreddit_urls: List[str], sent_photos: Set[str]) -> str:
    """Finds a new photo from the given subreddits."""
    headers = {"User-Agent": "telegram-bot"}
    for reddit_url in subreddit_urls:
        try:
            response = requests.get(reddit_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            posts = data.get("data", {}).get("children", [])
            for post in posts:
                post_data = post.get("data", {})
                url = post_data.get("url")
                title = post_data.get("title", "No title")
                if url and url.endswith(('.jpg', '.jpeg', '.png')) and url not in sent_photos:
                    return url, title
        except requests.RequestException as e:
            print(f"Error fetching {reddit_url}: {e}")
    return None, None

async def send_to_channel(channel_id: int, subreddit_urls: List[str], sent_photos: Dict[int, Set[str]]):
    """Sends a new photo to a specific channel if available."""
    try:
        
        photo_url, title = get_new_photo(subreddit_urls, sent_photos.get(channel_id, []))
        if photo_url:
            await bot.send_photo(
                chat_id=channel_id,
                photo=photo_url,
                caption=title[:200]  # Truncate long titles
            )
            sent_photos[channel_id].add(photo_url)
            save_sent_photos(sent_photos)
            print(f"Sent photo to channel {channel_id}")
        else:
            print(f"No new photos found for channel {channel_id}")
    except TelegramError as e:
        print(f"Telegram error for channel {channel_id}: {e}")

async def check_all_channels():
    """Checks all channels for new content."""
    sent_photos = load_sent_photos()
    tasks = []
    for channel_id, subreddit_urls in CHANNELS.items():
        tasks.append(send_to_channel(channel_id, subreddit_urls, sent_photos))
    await asyncio.gather(*tasks)

async def main():
    print(f"Bot started. Checking channels every {WAIT_TIME} minutes...")
    while True:
        await check_all_channels()
        await asyncio.sleep(60 * WAIT_TIME)

if __name__ == "__main__":
    # Initialize sent_photos file if it doesn't exist
    if not os.path.exists(SENT_PHOTOS_FILE):
        save_sent_photos({channel_id: set() for channel_id in CHANNELS})
    asyncio.run(main())
    