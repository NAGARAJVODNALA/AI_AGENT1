import os
import json
import time
import socket
import urllib.request
import urllib.error

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"].strip()
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()

def fetch_top_news(limit=8):
    top_ids_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    with urllib.request.urlopen(top_ids_url, timeout=15) as resp:
        story_ids = json.loads(resp.read().decode())[:limit]

    stories = []
    for sid in story_ids:
        item_url = f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
        with urllib.request.urlopen(item_url, timeout=15) as resp:
            item = json.loads(resp.read().decode())
            stories.append(f"- {item.get('title')} ({item.get('url', 'no link')})")
    return "\n".join(stories)

def ask_gemini(prompt):
    # Ordered from highest free-tier quota & newest stable models first
    models = [
        "gemini-3.5-flash-lite",
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.5-flash",
        "gemini-3.1-flash-lite",
    ]
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        for attempt in range(1, 3):
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=25) as resp:
                    data = json.loads(resp.read().decode())
                    print(f"Success using model: {model}")
                    return data["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="ignore")
                print(f"[{model} attempt {attempt}] HTTP {e.code}: {err_body[:150]}")
                if e.code == 404:
                    break
                if e.code in (429, 500, 503):
                    time.sleep(3 * attempt)
                    continue
                raise
            except (TimeoutError, socket.timeout, urllib.error.URLError) as e:
                print(f"[{model} attempt {attempt}] Network/Timeout error: {e}")
                time.sleep(2)
                continue

    raise RuntimeError("All models failed or timed out.")

def deliver_output(message):
    print("\n=== AI_AGENT1 BRIEFING ===\n")
    print(message)
    if DISCORD_WEBHOOK:
        req = urllib.request.Request(
            DISCORD_WEBHOOK,
            data=json.dumps({"content": message[:1900]}).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "AI-Agent/1.0"}
        )
        urllib.request.urlopen(req)

if __name__ == "__main__":
    raw_news = fetch_top_news(limit=8)
    prompt = (
        "You are AI_AGENT1, my daily tech & AI research agent. Review these live headlines, "
        "pick the 3 most important ones, and summarize why each matters in 2 bullet points:\n\n"
        f"{raw_news}"
    )
    briefing = ask_gemini(prompt)
    deliver_output(briefing)
