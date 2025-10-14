import os, time, random, json, sys
from datetime import datetime
import pandas as pd
import requests

# === CONFIG ===
CSV_PATH = "launch_1000_post_blitz_free_stack.csv"   # must match your CSV filename
STATE_PATH = "posted_state.json"                      # remembers what's posted
JITTER_SECONDS = (0, 30)                              # small random delay before each post

# Enable/disable channels (all free)
ENABLE = {
    "reddit_post": True,            # auto-post IF a subreddit env is set; else prints for manual paste
    "reddit_comment": True,         # prints for manual paste (safer than auto-replying)
    "discord_message": True,        # posts via Discord webhooks (free)
    "telegram_channel_post": True,  # posts via your Telegram bots (free)
    "indie_hackers": True,          # prints for manual paste
    "product_hunt_comment": True,   # prints for manual paste
}

# === Helpers ===
def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"done": {}}

def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def parse_time(s):
    if not s or not isinstance(s, str):
        return datetime.now()
    return datetime.strptime(s, "%Y-%m-%d %H:%M")  # must match CSV format

def spin_webhook():
    """Pick a random Discord webhook from DISCORD_WEBHOOK_URLS (comma-separated)."""
    urls = os.getenv("DISCORD_WEBHOOK_URLS", "").split(",")
    urls = [u.strip() for u in urls if u.strip()]
    return random.choice(urls) if urls else None

# === Reddit (PRAW) ===
def reddit_client():
    import praw
    return praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        username=os.getenv("REDDIT_USERNAME"),
        password=os.getenv("REDDIT_PASSWORD"),
        user_agent=os.getenv("REDDIT_USER_AGENT", "slotsniper-trialkiller/1.0"),
    )

def post_reddit(text, brand):
    """
    Reddit POST. If no subreddit env is set for the brand, print the post
    block for manual pasting (safest).
    text format: "TITLE: ...\n\nBODY..."
    """
    if "TITLE:" not in text:
        print("[reddit_post] invalid format (no TITLE:)"); return False
    title, body = text.split("\n\n", 1)
    title = title.replace("TITLE:", "").strip()
    body = body.strip()
    sub = os.getenv("REDDIT_SUB_SLOTSNIPER") if brand == "slotsniper" else os.getenv("REDDIT_SUB_TRIALKILLER")
    if not sub:
        print("\n[REDDIT POST — paste manually]")
        print("Subreddit: (choose per rules)")
        print("TITLE:", title)
        print("---- BODY ----\n" + body + "\n--------------\n")
        return True
    try:
        r = reddit_client()
        r.subreddit(sub).submit(title=title, selftext=body)
        return True
    except Exception as e:
        print("[reddit_post error]", e)
        return False

def post_reddit_comment(text):
    """We don't auto-reply to threads; print for manual contextual reply."""
    print("\n[REDDIT COMMENT — paste under relevant thread]\n" + text + "\n")
    return True

# === Discord ===
def post_discord(text):
    url = spin_webhook()
    if not url:
        print("[discord] No DISCORD_WEBHOOK_URLS set; printing for manual paste:\n", text)
        return True
    try:
        r = requests.post(url, json={"content": text}, timeout=10)
        if r.ok:
            return True
        print("[discord] non-200:", r.status_code, r.text)
        return False
    except Exception as e:
        print("[discord error]", e)
        return False

# === Telegram ===
def post_telegram_channel(text, brand):
    token = os.getenv("SLOTSNIPER_BOT_TOKEN") if brand == "slotsniper" else os.getenv("TRIALKILLER_BOT_TOKEN")
    chat  = os.getenv("SS_CHANNEL") if brand == "slotsniper" else os.getenv("TK_CHANNEL")
    if not token or not chat:
        print("[telegram] Missing token or channel; print instead:\n", text)
        return True
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": text, "disable_web_page_preview": True},
            timeout=10,
        )
        if r.ok:
            return True
        print("[telegram] non-200:", r.status_code, r.text)
        return False
    except Exception as e:
        print("[telegram error]", e)
        return False

def print_block(label, text):
    print(f"\n[{label} — paste manually]\n{text}\n")

# === One-shot run (for GitHub Actions schedule) ===
def one_shot_run():
    df = pd.read_csv(CSV_PATH)
    state = load_state()

    # sanity
    required = ["Post #", "Day/Time (local)", "Platform", "Brand", "Primary Copy"]
    for col in required:
        if col not in df.columns:
            print(f"CSV missing column: {col}")
            sys.exit(1)

    now = datetime.now()

    for _, row in df.iterrows():
        k = str(row["Post #"])
        if state["done"].get(k):
            continue

        when = parse_time(row["Day/Time (local)"])
        if when > now:
            continue  # not due yet

        # small jitter to avoid looking botty
        time.sleep(random.randint(*JITTER_SECONDS))

        platform = row["Platform"]
        brand    = row["Brand"]
        text     = row["Primary Copy"]

        ok = False
        try:
            if platform == "reddit_post" and ENABLE["reddit_post"]:
                ok = post_reddit(text, brand)
            elif platform == "reddit_comment" and ENABLE["reddit_comment"]:
                ok = post_reddit_comment(text)
            elif platform == "discord_message" and ENABLE["discord_message"]:
                ok = post_discord(text)
            elif platform == "telegram_channel_post" and ENABLE["telegram_channel_post"]:
                ok = post_telegram_channel(text, brand)
            elif platform == "indie_hackers" and ENABLE["indie_hackers"]:
                print_block("INDIE HACKERS", text); ok = True
            elif platform == "product_hunt_comment" and ENABLE["product_hunt_comment"]:
                print_block("PRODUCT HUNT COMMENT", text); ok = True
            else:
                print("[skip]", platform); ok = True
        except Exception as e:
            print("[error]", platform, e); ok = False

        if ok:
            state["done"][k] = True
            print(f"[posted] #{k} • {platform} • {brand}")
        else:
            print(f"[retry later] #{k} • {platform} • {brand}")

    save_state(state)

if __name__ == "__main__":
    one_shot_run()
