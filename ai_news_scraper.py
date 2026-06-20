import requests
import feedparser
import time

R = 'https://diygodrsshubchromium-bundled-production-4500.up.railway.app' # RSSHub fallback URL

feeds = [
    { 'url': 'https://openai.com/news/rss.xml', 'company': 'OpenAI' },
    { 'url': 'https://deepmind.google/blog/rss.xml', 'company': 'Google DeepMind' },
    { 'url': 'https://huggingface.co/blog/feed.xml', 'company': 'Hugging Face' },
    { 'url': 'https://blog.langchain.dev/rss/', 'company': 'LangChain' },
    { 'url': 'https://cursor.com/rss.xml', 'company': 'Cursor' },
    { 'url': 'https://stability.ai/news?format=rss', 'company': 'Stability AI' },
    { 'url': 'https://blog.replit.com/feed.xml', 'company': 'Replit' },

    # GitHub Releases (8)
    { 'url': 'https://github.com/anthropics/anthropic-sdk-python/releases.atom', 'company': 'Anthropic' },
    { 'url': 'https://github.com/ollama/ollama/releases.atom', 'company': 'Ollama' },
    { 'url': 'https://github.com/facebookresearch/llama/releases.atom', 'company': 'Meta AI' },
    { 'url': 'https://github.com/deepseek-ai/DeepSeek-V3/releases.atom', 'company': 'DeepSeek' },
    { 'url': 'https://github.com/QwenLM/qwen-code/releases.atom', 'company': 'Qwen' },
    { 'url': 'https://github.com/mistralai/client-python/releases.atom', 'company': 'Mistral AI' },
    { 'url': 'https://github.com/xai-org/grok-build/releases.atom', 'company': 'xAI' },
    { 'url': 'https://github.com/huggingface/transformers/releases.atom', 'company': 'Hugging Face' },

    # Twitter via RSSHub (6)
    { 'url': R + '/twitter/user/OpenAI', 'company': 'OpenAI' },
    { 'url': R + '/twitter/user/AnthropicAI', 'company': 'Anthropic' },
    { 'url': R + '/twitter/user/GoogleDeepMind', 'company': 'Google DeepMind' },
    { 'url': R + '/twitter/user/HuggingFace', 'company': 'Hugging Face' },
    { 'url': R + '/twitter/user/MistralAI', 'company': 'Mistral AI' },
    { 'url': R + '/twitter/user/GroqInc', 'company': 'Groq' }
]

def fetch_feed(feed_info, limit=5):
    url = feed_info['url']
    company = feed_info['company']
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        feed = feedparser.parse(response.content)
        items = []

        for entry in feed.entries[:limit]:
            title = entry.get('title', 'No Title')
            link = entry.get('link', '')

            # published or updated date
            pub_date = entry.get('published', entry.get('updated', entry.get('pubDate', 'No Date')))

            items.append({
                'company': company,
                'title': title,
                'link': link,
                'pub_date': pub_date
            })

        return items
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []

def main():
    all_news = []

    print(f"Scraping {len(feeds)} feeds...")
    for i, feed in enumerate(feeds):
        print(f"[{i+1}/{len(feeds)}] Fetching {feed['company']} ({feed['url']})")
        items = fetch_feed(feed, limit=2) # Get up to 2 items per feed for brevity
        all_news.extend(items)
        time.sleep(1) # Be polite

    print("\n--- Scraped News ---\n")
    for idx, item in enumerate(all_news, 1):
        print(f"{idx}. [{item['company']}] {item['title']}")
        print(f"   Date: {item['pub_date']}")
        print(f"   Link: {item['link']}\n")

if __name__ == "__main__":
    main()
