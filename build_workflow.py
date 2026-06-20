import json

def build():
    workflow = {
      "name": "AI News Aggregator",
      "nodes": [
        {
          "name": "Schedule Trigger (daily)",
          "type": "n8n-nodes-base.scheduleTrigger",
          "typeVersion": 1.1,
          "position": [0, 200],
          "parameters": {
            "rule": {
              "interval": [{"field": "days"}]
            }
          }
        },
        {
          "name": "Init DB & Get Existing Links",
          "type": "n8n-nodes-base.postgres",
          "typeVersion": 2.3,
          "position": [200, 200],
          "parameters": {
            "operation": "executeQuery",
            "query": "CREATE TABLE IF NOT EXISTS ai_news_queue ( \n  link TEXT PRIMARY KEY, \n  company TEXT, \n  title TEXT, \n  ai_summary TEXT, \n  status VARCHAR(20) DEFAULT 'pending', \n  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP \n); \n\nSELECT link FROM ai_news_queue;"
          },
          "credentials": {
            "postgres": {
              "id": "zdmSZhJPgnAdWsoT",
              "name": "Postgres account"
            }
          },
          "continueOnFail": True
        },
        {
          "name": "Fetch & Parse RSS Feeds",
          "type": "n8n-nodes-base.code",
          "typeVersion": 2,
          "position": [400, 200],
          "parameters": {
            "jsCode": """const R = 'https://diygodrsshubchromium-bundled-production-4500.up.railway.app';
const feeds = [
  { url: 'https://openai.com/news/rss.xml', company: 'OpenAI' },
  { url: 'https://deepmind.google/blog/rss.xml', company: 'Google DeepMind' },
  { url: 'https://huggingface.co/blog/feed.xml', company: 'Hugging Face' },
  { url: 'https://blog.langchain.dev/rss/', company: 'LangChain' },
  { url: 'https://cursor.com/rss.xml', company: 'Cursor' },
  { url: 'https://stability.ai/news?format=rss', company: 'Stability AI' },
  { url: 'https://blog.replit.com/feed.xml', company: 'Replit' },
  { url: 'https://github.com/anthropics/anthropic-sdk-python/releases.atom', company: 'Anthropic' },
  { url: 'https://github.com/ollama/ollama/releases.atom', company: 'Ollama' },
  { url: 'https://github.com/facebookresearch/llama/releases.atom', company: 'Meta AI' },
  { url: 'https://github.com/deepseek-ai/DeepSeek-V3/releases.atom', company: 'DeepSeek' },
  { url: 'https://github.com/QwenLM/qwen-code/releases.atom', company: 'Qwen' },
  { url: 'https://github.com/mistralai/client-python/releases.atom', company: 'Mistral AI' },
  { url: 'https://github.com/xai-org/grok-build/releases.atom', company: 'xAI' },
  { url: 'https://github.com/huggingface/transformers/releases.atom', company: 'Hugging Face' },
  { url: R + '/twitter/user/OpenAI', company: 'OpenAI' },
  { url: R + '/twitter/user/AnthropicAI', company: 'Anthropic' },
  { url: R + '/twitter/user/GoogleDeepMind', company: 'Google DeepMind' },
  { url: R + '/twitter/user/HuggingFace', company: 'Hugging Face' },
  { url: R + '/twitter/user/MistralAI', company: 'Mistral AI' },
  { url: R + '/twitter/user/GroqInc', company: 'Groq' }
];

const existingLinksInput = $('Init DB & Get Existing Links').all();
const existingLinks = new Set(
  existingLinksInput
    .map(item => item.json.link)
    .filter(link => link)
    .map(link => String(link).trim().toLowerCase())
);

// XML Parser helper
function getTagValue(xml, tag) {
  const regex = new RegExp(`<${tag}[^>]*>([\\\\s\\\\S]*?)</${tag}>`, 'i');
  const match = xml.match(regex);
  if (match) {
    return match[1].replace(/<!\\[CDATA\\[([\\s\\S]*?)\\]\\]>/g, '$1').trim();
  }
  return null;
}

function cleanHtml(str) {
  if (!str) return '';
  return str.replace(/<[^>]*>/g, '').replace(/&[a-z]+;/gi, ' ').trim();
}

async function fetchFeed(feed) {
  try {
    const res = await fetch(feed.url, { timeout: 15000 });
    if (!res.ok) return [];
    const text = await res.text();

    // Naive split by item or entry
    let blocks = text.split(/<item>|<entry>/i).slice(1); // skip header

    const items = [];
    for (let i = 0; i < Math.min(blocks.length, 5); i++) {
      const block = blocks[i];
      let title = getTagValue(block, 'title') || '';
      let link = getTagValue(block, 'link') || '';
      // handle <link href="..."/> in Atom
      if (!link) {
        const linkMatch = block.match(/<link[^>]+href=["']([^"']+)["']/i);
        if (linkMatch) link = linkMatch[1];
      }
      let content = getTagValue(block, 'description') || getTagValue(block, 'content') || getTagValue(block, 'summary') || '';
      let pubDate = getTagValue(block, 'pubDate') || getTagValue(block, 'updated') || getTagValue(block, 'published') || '';

      link = link.trim();
      if (!link || link.length < 5) continue;

      const cleanLink = link.toLowerCase();
      if (existingLinks.has(cleanLink)) continue;

      items.push({
        title: cleanHtml(title),
        link: link,
        content: cleanHtml(content).substring(0, 300),
        pubDate: pubDate,
        company: feed.company,
        timestamp: new Date(pubDate || new Date()).getTime()
      });
    }
    return items;
  } catch(e) {
    return [];
  }
}

const BATCH = 5;
const DELAY = 800;
let allItems = [];

for (let i = 0; i < feeds.length; i += BATCH) {
  const batch = feeds.slice(i, i + BATCH);
  const results = await Promise.allSettled(batch.map(feed => fetchFeed(feed)));
  for (const res of results) {
    if (res.status === 'fulfilled') {
      allItems.push(...res.value);
    }
  }
  if (i + BATCH < feeds.length) {
    await new Promise(r => setTimeout(r, DELAY));
  }
}

// Sort by date (newest first)
allItems.sort((a, b) => b.timestamp - a.timestamp);

// Deduplicate by link
const seen = new Set();
const finalItems = [];
for (const item of allItems) {
  const cl = item.link.toLowerCase();
  if (!seen.has(cl)) {
    seen.add(cl);
    finalItems.push({
      json: {
        link: item.link,
        company: item.company,
        title: item.title,
        content: item.content,
        pubDate: item.pubDate
      }
    });
  }
}

return finalItems;"""
          },
          "continueOnFail": True
        },
        {
          "name": "Fetch Jina AI & Preserve Data",
          "type": "n8n-nodes-base.code",
          "typeVersion": 2,
          "position": [600, 200],
          "parameters": {
            "jsCode": """const items = $input.all();
const results = [];
const BATCH = 5;
const DELAY = 2000;

for (let i = 0; i < items.length; i += BATCH) {
  const batch = items.slice(i, i + BATCH);
  const promises = batch.map(async (item) => {
    let jinaContent = '';
    const link = item.json.link;
    if (link) {
      try {
        const res = await fetch('https://r.jina.ai/' + link, {
          headers: { 'Accept': 'application/json' },
          timeout: 30000
        });
        if (res.ok) {
          const data = await res.json();
          if (data && data.data && data.data.content) {
            jinaContent = String(data.data.content).substring(0, 3000);
          }
        }
      } catch(e) {
        // ignore error and fallback to empty jinaContent
      }
    }

    return {
      json: {
        link: String(item.json.link || '').trim(),
        company: item.json.company || 'Unknown',
        title: String(item.json.title || '').trim(),
        pubDate: item.json.pubDate || '',
        rss_content: String(item.json.content || '').substring(0, 500),
        jina_content: jinaContent
      }
    };
  });

  const batchRes = await Promise.all(promises);
  results.push(...batchRes);

  if (i + BATCH < items.length) {
    await new Promise(r => setTimeout(r, DELAY));
  }
}

return results;"""
          },
          "continueOnFail": True
        },
        {
          "name": "AI Summarize via DeepSeek",
          "type": "n8n-nodes-base.code",
          "typeVersion": 2,
          "position": [800, 200],
          "parameters": {
            "jsCode": """const mergedItems = $input.all();
const SYSTEM_PROMPT = `شما خبرنگار تخصصی هوش مصنوعی هستید. خبر را در ۱ الی ۳ خط به فارسی روان خلاصه کنید.

قوانین حیاتی:
۱. ابتدا تشخیص دهید موضوع خبر چیست و یک کلمه فارسی مناسب در ابتدای جمله بگذارید:
   - شرکت/سازمان: "شرکت"
   - مدل هوش مصنوعی: "مدل"
   - ابزار/پلتفرم: "پلتفرم"
   - ایجنت: "ایجنت"
   - فریمورک/کتابخانه: "فریمورک"
   - پژوهش: "پژوهش"
   - محصول: "محصول"
۲. ایموجی مرتبط در ابتدای جمله.
۳. نام شرکت‌ها و مدل‌ها را در تگ <code> قرار دهید.
۴. فقط از تگ‌های HTML مجاز تلگرام (<b>, <i>, <code>, <a>) استفاده کنید.
۵. هشتگ فارسی مرتبط در انتها بزنید.
۶. اگر خبر بی‌اهمیت است فقط بنویسید: SKIP
۷. فقط خلاصه خبر، بدون توضیح اضافه.`;

async function getSummary(itemJson) {
  const body = JSON.stringify({
    model: 'deepseek-v4-flash',
    messages: [
      { role: 'system', content: SYSTEM_PROMPT },
      { role: 'user', content: `Company: ${itemJson.company}\\nTitle: ${itemJson.title}\\nContent: ${itemJson.jina_content || itemJson.rss_content}` }
    ],
    temperature: 0.2
  });

  try {
    const res = await fetch('https://api.gapgpt.app/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer sk-mWwh3PFftshR4DtuWGDD4Rk7MegNtoe595gpLnP46cGUrOiH'
      },
      body: body,
      timeout: 30000
    });

    if (!res.ok) return '';
    const data = await res.json();
    return data.choices?.[0]?.message?.content || '';
  } catch(e) {
    return '';
  }
}

const BATCH = 5;
const DELAY = 800;
const results = [];

for (let i = 0; i < mergedItems.length; i += BATCH) {
  const batch = mergedItems.slice(i, i + BATCH);
  const promises = batch.map(async (item) => {
    let summary = await getSummary(item.json);

    if (summary.includes('SKIP') || summary.trim() === '') {
      return null;
    }

    // Clean summary
    summary = summary
      .replace(/<(?!(?:\\/?b|\\/?i|\\/?code|\\/?a)(?:>|\\s+[^>]*>))[^>]*>/gi, '') // strip any HTML except allowed
      .replace(/\\*\\*/g, '')           // strip markdown bold
      .replace(/```[\\s\\S]*?```/g, '') // strip code blocks
      .replace(/\\n{2,}/g, '\\n')       // collapse multiple newlines
      .trim();

    return {
      json: {
        link: item.json.link,
        company: item.json.company,
        title: item.json.title,
        ai_summary: summary
      }
    };
  });

  const batchRes = await Promise.allSettled(promises);
  for (const r of batchRes) {
    if (r.status === 'fulfilled' && r.value !== null) {
      results.push(r.value);
    }
  }

  if (i + BATCH < mergedItems.length) {
    await new Promise(r => setTimeout(r, DELAY));
  }
}

return results;"""
          },
          "continueOnFail": True
        },
        {
          "name": "Validate & Clean Results",
          "type": "n8n-nodes-base.code",
          "typeVersion": 2,
          "position": [1000, 200],
          "parameters": {
            "jsCode": "return $input.all().filter(item => {\n  const j = item.json;\n  return j.link && j.link.length > 5 && j.ai_summary && j.ai_summary.length > 10;\n});"
          },
          "continueOnFail": True
        },
        {
          "name": "Save to DB as 'pending'",
          "type": "n8n-nodes-base.postgres",
          "typeVersion": 2.3,
          "position": [1200, 200],
          "parameters": {
            "operation": "executeQuery",
            "query": "={{ `INSERT INTO ai_news_queue (link, company, title, ai_summary, status) VALUES ('${$json.link.replace(/'/g, \"''\")}', '${$json.company.replace(/'/g, \"''\")}', '${$json.title.replace(/'/g, \"''\")}', '${$json.ai_summary.replace(/'/g, \"''\")}', 'pending') ON CONFLICT (link) DO NOTHING;` }}"
          },
          "credentials": {
            "postgres": {
              "id": "zdmSZhJPgnAdWsoT",
              "name": "Postgres account"
            }
          }
        },
        {
          "name": "Schedule Trigger (every 2h)",
          "type": "n8n-nodes-base.scheduleTrigger",
          "typeVersion": 1.1,
          "position": [0, 500],
          "parameters": {
            "rule": {
              "interval": [{"field": "hours", "hoursInterval": 2}]
            }
          }
        },
        {
          "name": "Get 1 Pending News",
          "type": "n8n-nodes-base.postgres",
          "typeVersion": 2.3,
          "position": [200, 500],
          "parameters": {
            "operation": "executeQuery",
            "query": "SELECT * FROM ai_news_queue WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1;"
          },
          "credentials": {
            "postgres": {
              "id": "zdmSZhJPgnAdWsoT",
              "name": "Postgres account"
            }
          },
          "continueOnFail": True
        },
        {
          "name": "IF has result",
          "type": "n8n-nodes-base.if",
          "typeVersion": 1,
          "position": [400, 500],
          "parameters": {
            "conditions": {
              "string": [
                {
                  "value1": "={{ $json.link }}",
                  "operation": "isNotEmpty"
                }
              ]
            }
          },
          "continueOnFail": True
        },
        {
          "name": "Send to Telegram",
          "type": "n8n-nodes-base.code",
          "typeVersion": 2,
          "position": [600, 400],
          "parameters": {
            "jsCode": """const summary = $json.ai_summary;
await this.helpers.httpRequest({
  method: 'POST',
  url: 'https://api.telegram.org/bot8453602531:AAGmzqyUspjIA9BDFFfUC-4DeIwZu-eYVQY/sendMessage',
  body: {
    chat_id: '-1002176426998',
    text: summary,
    parse_mode: 'HTML',
    disable_web_page_preview: true
  },
  json: true
});
return [{json: $json}];"""
          },
          "continueOnFail": True
        },
        {
          "name": "Mark as 'published'",
          "type": "n8n-nodes-base.postgres",
          "typeVersion": 2.3,
          "position": [800, 400],
          "parameters": {
            "operation": "executeQuery",
            "query": "={{ `UPDATE ai_news_queue SET status = 'published' WHERE link = '${$json.link.replace(/'/g, \"''\")}';` }}"
          },
          "credentials": {
            "postgres": {
              "id": "zdmSZhJPgnAdWsoT",
              "name": "Postgres account"
            }
          }
        }
      ],
      "connections": {
        "Schedule Trigger (daily)": {
          "main": [
            [{"node": "Init DB & Get Existing Links", "type": "main", "index": 0}]
          ]
        },
        "Init DB & Get Existing Links": {
          "main": [
            [{"node": "Fetch & Parse RSS Feeds", "type": "main", "index": 0}]
          ]
        },
        "Fetch & Parse RSS Feeds": {
          "main": [
            [{"node": "Fetch Jina AI & Preserve Data", "type": "main", "index": 0}]
          ]
        },
        "Fetch Jina AI & Preserve Data": {
          "main": [
            [{"node": "AI Summarize via DeepSeek", "type": "main", "index": 0}]
          ]
        },
        "AI Summarize via DeepSeek": {
          "main": [
            [{"node": "Validate & Clean Results", "type": "main", "index": 0}]
          ]
        },
        "Validate & Clean Results": {
          "main": [
            [{"node": "Save to DB as 'pending'", "type": "main", "index": 0}]
          ]
        },
        "Schedule Trigger (every 2h)": {
          "main": [
            [{"node": "Get 1 Pending News", "type": "main", "index": 0}]
          ]
        },
        "Get 1 Pending News": {
          "main": [
            [{"node": "IF has result", "type": "main", "index": 0}]
          ]
        },
        "IF has result": {
          "main": [
            [{"node": "Send to Telegram", "type": "main", "index": 0}]
          ]
        },
        "Send to Telegram": {
          "main": [
            [{"node": "Mark as 'published'", "type": "main", "index": 0}]
          ]
        }
      },
      "active": False,
      "settings": {
        "executionOrder": "v1"
      }
    }

    with open('/app/workflow.json', 'w', encoding='utf-8') as f:
        json.dump(workflow, f, indent=2, ensure_ascii=False)
        print("Generated workflow.json")

if __name__ == '__main__':
    build()
