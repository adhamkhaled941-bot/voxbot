import os, json
import requests
from bs4 import BeautifulSoup

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
URLS = [u.strip() for u in os.environ.get("VOX_URLS", "").split(",") if u.strip()]
STATE_FILE = "state.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def send(msg):
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg[:4000], "disable_web_page_preview": True},
        timeout=20,
    )
    print("telegram:", r.status_code)

def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def get_lines(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    lines = set()
    for line in soup.get_text("\n").split("\n"):
        line = " ".join(line.split())
        if 2 < len(line) < 200:
            lines.add(line)
    return sorted(lines)

def main():
    if not URLS:
        print("No VOX_URLS set")
        return
    state = load_state()
    for url in URLS:
        old = state.get(url)
        try:
            lines = get_lines(url)
        except Exception as e:
            print("fetch error:", e)
            if not (old and old.get("failed")):
                send(f"VOX bot: could not open {url}\n{e}")
            state[url] = {"lines": old["lines"] if old else [], "failed": True}
            continue
        if old is None:
            msg = f"VOX bot is now tracking:\n{url}\nItems found: {len(lines)}"
            if len(lines) < 20:
                msg += "\nWarning: very little content. The page may load data with JavaScript."
            send(msg)
        else:
            new = [l for l in lines if l not in set(old["lines"])]
            if new:
                send("New on VOX:\n" + "\n".join("- " + l for l in new[:40]) + "\n\n" + url)
        state[url] = {"lines": lines, "failed": False}
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)

main()
