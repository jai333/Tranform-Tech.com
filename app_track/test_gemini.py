import os
import json
from openai import OpenAI
from dotenv import load_dotenv
import requests

load_dotenv()
api_key = os.environ.get('OPENAI_API_KEY')
print("Base URL:", os.environ.get('OPENAI_BASE_URL'))

client = OpenAI(api_key=api_key)

try:
    response = client.chat.completions.create(
        model="gemini-1.5-flash",
        messages=[
            {"role": "system", "content": "You are a specialized JSON-output sales intelligence bot."},
            {"role": "user", "content": "Return a simple JSON with key 'test' and value 'success'"}
        ],
        temperature=0.9,
    )
    print("Gemini API Success:", response.choices[0].message.content)
except Exception as e:
    print("Gemini API Error:", e)

# Also test SerpAPI
serp_api_key = os.environ.get('SERP_API_KEY')
if serp_api_key:
    params = {
        "engine": "google_news",
        "q": "CallSphere Inc (funding OR expansion OR hiring OR acquisition)",
        "api_key": serp_api_key,
        "num": 3
    }
    try:
        res = requests.get("https://serpapi.com/search", params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        print("SerpAPI Success:", len(data.get("news_results", [])))
    except Exception as e:
        print("SerpAPI Error:", e)
