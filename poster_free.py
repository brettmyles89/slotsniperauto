import os
import sys
import time
import json
import random
from datetime import datetime

import pandas as pd
import requests

# === CONFIG ===
CSV_PATH = "launch_5000_72h_multiplatform_free_NO_MEDIUM.csv"  # must match your CSV filename
STATE_PATH = "posted_state.json"                                # remembers what's posted
JITTER_SECONDS = (0, 30)                                        # small random delay before each post

# Enable/disable channels (all free)
ENABLE = {
    "mastodon": True,
    "bluesky": True,
    "lemmy": True,
    "tumblr": True,
    "devto": True,
    "medium": False,  # leave False if you're not posting to Medium in this script
    "hashnode": True,
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
    if platform == "reddit_post" and ENABLE.get("reddit_post"):
        ok = post_reddit(text, brand)
    elif platform == "reddit_comment" and ENABLE.get("reddit_comment"):
        ok = post_reddit_comment(text)
    elif platform == "discord_message" and ENABLE.get("discord_message"):
        ok = post_discord(text)
    elif platform == "telegram_channel_post" and ENABLE.get("telegram_channel_post"):
        ok = post_telegram_channel(text, brand)
    elif platform == "indie_hackers" and ENABLE.get("indie_hackers"):
        print_block("INDIE HACKERS", text); ok = True
    elif platform == "product_hunt_comment" and ENABLE.get("product_hunt_comment"):
        print_block("PRODUCT HUNT COMMENT", text); ok = True
    elif platform == "mastodon" and ENABLE.get("mastodon"):
        ok = post_mastodon(text)
    elif platform == "bluesky" and ENABLE.get("bluesky"):
        ok = post_bluesky(text)
    elif platform == "lemmy" and ENABLE.get("lemmy"):
        ok = post_lemmy(text)
    elif platform == "tumblr" and ENABLE.get("tumblr"):
        ok = post_tumblr(text)
    elif platform == "devto" and ENABLE.get("devto"):
        ok = post_devto(text)
    elif platform == "medium" and ENABLE.get("medium"):
        ok = post_medium(text)
    elif platform == "hashnode" and ENABLE.get("hashnode"):
        ok = post_hashnode(text)
    else:
        print(f"Skipping unknown or disabled platform: {platform}")
        ok = False
except Exception as e:
    ok = False
    print(f"[ERROR] {platform}: {e}")

    save_state(state)

def post_mastodon(text: str) -> bool:
    try:
        from mastodon import Mastodon
        base = os.getenv("MASTODON_BASE_URL")       # e.g., https://mastodon.social
        token = os.getenv("MASTODON_ACCESS_TOKEN")  # user access token
        if not base or not token:
            print("[mastodon] missing env; printing instead:\n", text)
            return True
        m = Mastodon(api_base_url=base, access_token=token)
        m.status_post(text[:500])
        return True
    except Exception as e:
        print(f"[mastodon] error: {e}")
        return False


# --- keep this at the very bottom of the file ---
if __name__ == "__main__":
    one_shot_run()

def post_bluesky(text):
    try:
        from atproto import Client
        ident = os.getenv("BLUESKY_IDENTIFIER")   # handle or email
        pwd = os.getenv("BLUESKY_PASSWORD")       # **app password**
        if not ident or not pwd:
            print("[bluesky] missing env; printing:\n", text); return True
        c = Client()
        c.login(ident, pwd)
        c.send_post(text[:300])
        return True
    except Exception as e:
        print("[bluesky error]", e); return False
def post_lemmy(text):
    # Expects a TITLE block like reddit; else falls back to short post
    base = os.getenv("LEMMY_BASE_URL")   # e.g., https://lemmy.world
    user = os.getenv("LEMMY_USERNAME")
    pwd  = os.getenv("LEMMY_PASSWORD")
    comm = os.getenv("LEMMY_COMMUNITY_ID")  # numeric id OR 'name@instance' depending on API
    if not base or not user or not pwd or not comm:
        print("[lemmy] missing env; printing:\n", text); return True
    try:
        import requests
        # login
        r = requests.post(f"{base}/api/v3/user/login", json={"username_or_email": user, "password": pwd}, timeout=15)
        jwt = r.json().get("jwt")
        if not jwt:
            print("[lemmy] login failed:", r.text); return False
        # parse title/body
        if "TITLE:" in text:
            title, body = text.split("\n\n", 1)
            title = title.replace("TITLE:","").strip()
            body = body.strip()
        else:
            title = text[:140]
            body = text
        # create post
        r2 = requests.post(f"{base}/api/v3/post", json={
            "name": title, "body": body, "community_id": int(comm)
        }, headers={"Authorization": f"Bearer {jwt}"}, timeout=15)
        ok = r2.ok
        if not ok: print("[lemmy]", r2.status_code, r2.text)
        return ok
    except Exception as e:
        print("[lemmy error]", e); return False
def post_tumblr(text):
    try:
        import pytumblr
        ck = os.getenv("TUMBLR_CONSUMER_KEY")
        cs = os.getenv("TUMBLR_CONSUMER_SECRET")
        ot = os.getenv("TUMBLR_OAUTH_TOKEN")
        osk= os.getenv("TUMBLR_OAUTH_SECRET")
        blog = os.getenv("TUMBLR_BLOG_IDENTIFIER")  # e.g., yourblog.tumblr.com
        if not all([ck,cs,ot,osk,blog]):
            print("[tumblr] missing env; printing:\n", text); return True
        client = pytumblr.TumblrRestClient(ck, cs, ot, osk)
        # Split first line as title if present
        if "TITLE:" in text:
            title, body = text.split("\n\n",1)
            title = title.replace("TITLE:","").strip()
            body = body.strip()
            client.create_text(blog, state="published", title=title, body=body)
        else:
            client.create_text(blog, state="published", body=text)
        return True
    except Exception as e:
        print("[tumblr error]", e); return False
def post_devto(text):
    key = os.getenv("DEVTO_API_KEY")
    if not key:
        print("[devto] missing API key; printing:\n", text); return True
    try:
        import requests
        # Extract title/body
        if "TITLE:" in text:
            title, body = text.split("\n\n",1)
            title = title.replace("TITLE:","").strip()
            body = body.strip()
        else:
            title = text.split("\n")[0][:60]
            body = text
        r = requests.post("https://dev.to/api/articles",
                          headers={"api-key": key, "Content-Type":"application/json"},
                          json={"article":{"title": title, "body_markdown": body, "published": True}},
                          timeout=20)
        if not r.ok: print("[devto]", r.status_code, r.text)
        return r.ok
    except Exception as e:
        print("[devto error]", e); return False
def post_medium(text):
    token = os.getenv("MEDIUM_INTEGRATION_TOKEN")
    user_id = os.getenv("MEDIUM_USER_ID")  # you can fetch via API once; paste here
    if not token or not user_id:
        print("[medium] missing env; printing:\n", text); return True
    try:
        import requests, json as _json
        if "TITLE:" in text:
            title, body = text.split("\n\n",1)
            title = title.replace("TITLE:","").strip()
            body = body.strip()
        else:
            title = text.split("\n")[0][:60]
            body = text
        r = requests.post(f"https://api.medium.com/v1/users/{user_id}/posts",
                          headers={"Authorization": f"Bearer {token}","Content-Type":"application/json"},
                          data=_json.dumps({"title": title, "contentFormat":"markdown", "content": body, "publishStatus":"public"}),
                          timeout=20)
        if not r.ok: print("[medium]", r.status_code, r.text)
        return r.ok
    except Exception as e:
        print("[medium error]", e); return False
def post_hashnode(text):
    token = os.getenv("HASHNODE_TOKEN")
    pub_id = os.getenv("HASHNODE_PUBLICATION_ID")  # optional; else personal blog
    if not token:
        print("[hashnode] missing token; printing:\n", text); return True
    try:
        import requests
        if "TITLE:" in text:
            title, body = text.split("\n\n",1)
            title = title.replace("TITLE:","").strip()
            body = body.strip()
        else:
            title = text.split("\n")[0][:60]
            body = text
        q = """
        mutation PublishPost($input: CreateStoryInput!){
          createStory(input: $input){ code success message }
        }
        """
        variables = {"input":{"title": title, "contentMarkdown": body}}
        if pub_id:
            variables["input"]["publicationId"] = pub_id
        r = requests.post("https://api.hashnode.com",
                          headers={"Content-Type":"application/json","Authorization": token},
                          json={"query": q, "variables": variables},
                          timeout=20)
        if not r.ok: print("[hashnode]", r.status_code, r.text)
        return r.ok
    except Exception as e:
        print("[hashnode error]", e); return False

