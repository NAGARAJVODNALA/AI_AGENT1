import os
import json
import urllib.request

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL")

# 1. THE TOOL: Fetches live top stories from Hacker News API (free, no key needed)
def fetch_top_news(limit=8):
    top_ids_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    with urllib.request.urlopen(top_ids_url) as resp:
        story_ids = json.loads(resp.read().decode())[:limit]

    stories = []
    for sid in story_ids:
        item_url = f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
        with urllib.request.urlopen(item_url) as resp:
            item = json.loads(resp.read().decode())
            stories.append(f"- {item.get('title')} ({item.get('url', 'no link')})")
    return "\n".join(stories)

# 2. THE BRAIN: Calls Google's free Gemini 3.8 Flash API
def ask_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        return data["candidates"][0]["content"]["parts"][0]["text"]

# 3. THE ACTION: Sends output to Discord (if configured) and prints to logs
def deliver_output(message):
    print("=== AGENT BRIEFING ===\n", message)
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
        "You are my daily tech & AI research agent. Review these live headlines, "
        "pick the 3 most important ones, and summarize why each matters in 2 bullet points:\n\n"
        f"{raw_news}"
    )
    briefing = ask_gemini(prompt)
    deliver_output(briefing)
