import os
import requests
import gradio as gr

API_KEY = os.environ.get("NEWS_API_KEY")
BASE = "https://newsapi.org/v2"
MAX_ARTICLES = 8


def fetch(url, params):
    params["apiKey"] = API_KEY
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json().get("articles", [])


def get_articles():
    # 1) India top headlines, 2) world / geopolitics
    india = fetch(f"{BASE}/top-headlines", {"country": "in", "pageSize": 20})
    world = fetch(
        f"{BASE}/everything",
        {
            "q": "geopolitics OR war OR economy OR diplomacy OR election",
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 20,
        },
    )

    # Mix: roughly 5 India + 3 world, remove duplicates and junk
    seen, picked = set(), []
    for art in india[:10] + world[:10]:
        title = (art.get("title") or "").strip()
        if not title or title == "[Removed]" or title in seen:
            continue
        seen.add(title)
        picked.append(art)

    return picked[:MAX_ARTICLES]


def render():
    if not API_KEY:
        return "⚠️ NEWS_API_KEY secret is missing. Add it in Space settings."
    try:
        articles = get_articles()
    except Exception as e:
        return f"⚠️ Could not fetch news: {e}"

    if not articles:
        return "No articles found."

    cards = []
    for a in articles:
        source = a["source"]["name"]
        desc = a.get("description") or ""
        cards.append(
            f"### [{a['title']}]({a['url']})\n"
            f"*{source} · {a.get('publishedAt', '')[:10]}*\n\n"
            f"{desc}\n\n---"
        )
    return "\n\n".join(cards)


with gr.Blocks(title="Deep News") as demo:
    gr.Markdown("# 📰 Deep News\nIndia first, the world in context.")
    btn = gr.Button("Refresh news")
    out = gr.Markdown()
    demo.load(render, outputs=out)   # loads on page open
    btn.click(render, outputs=out)

demo.launch()
