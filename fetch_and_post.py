#!/usr/bin/env python3
import os
import requests
from bs4 import BeautifulSoup
import openai
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ─── CONFIGURATION ────────────────────────────────────────────────────────────

# 1) Replace with your numeric Blog ID (from the URL in your dashboard)
BLOG_ID = "YOUR_BLOG_ID"

# 2) Add your scholarship sources here.
#    Each entry is (page_url, css_selector_for_each_item)
#    You can also use RSS URLs if you prefer.
SOURCES = [
    # ("https://example.com/scholarships", ".listing-item"),
]

# 3) Which OpenAI model to use for summaries
OPENAI_MODEL = "gpt-3.5-turbo"

# ─── AUTHENTICATE TO BLOGGER ────────────────────────────────────────────────────

def authenticate_blogger():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/blogger"]
    )
    creds.refresh(Request())
    return build("blogger", "v3", credentials=creds)

# ─── SCRAPE SCHOLARSHIP LISTINGS ────────────────────────────────────────────────

def fetch_scholarships():
    out = []
    for url, selector in SOURCES:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for item in soup.select(selector):
            title_el = item.select_one(".title")
            link_el  = item.select_one("a")
            country_el  = item.select_one(".country")
            deadline_el = item.select_one(".deadline")

            title    = title_el.get_text(strip=True) if title_el else "No title"
            link     = link_el["href"]         if link_el  else ""
            country  = country_el.get_text(strip=True) if country_el  else ""
            deadline = deadline_el.get_text(strip=True) if deadline_el else ""

            out.append({
                "title": title,
                "link": link,
                "country": country,
                "deadline": deadline
            })
    return out

# ─── GENERATE ACADEMIC SUMMARY ─────────────────────────────────────────────────

def summarize_entry(entry: dict) -> str:
    openai.api_key = os.environ["OPENAI_API_KEY"]
    prompt = (
        f"Write a concise 2–3 sentence summary for this scholarship opportunity:\n\n"
        f"Title: {entry['title']}\n"
        f"Country: {entry['country']}\n"
        f"Deadline: {entry['deadline']}\n"
        f"Link: {entry['link']}\n"
    )
    resp = openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are an expert educational advisor."},
            {"role": "user",   "content": prompt}
        ],
        max_tokens=100,
        temperature=0.7
    )
    return resp.choices[0].message.content.strip()

# ─── PUBLISH TO BLOGGER ────────────────────────────────────────────────────────

def post_to_blogger(service, entry: dict):
    summary = summarize_entry(entry)
    content = (
        f"<p>{summary}</p>"
        f"<p><a href=\"{entry['link']}\">Apply Here</a></p>"
    )
    body = {
        "kind": "blogger#post",
        "blog": {"id": BLOG_ID},
        "title": entry["title"],
        "content": content
    }
    result = service.posts().insert(blogId=BLOG_ID, body=body).execute()
    print(f"Published: {result['url']}")

# ─── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    if BLOG_ID == "YOUR_BLOG_ID":
        raise SystemExit("❌ Please edit fetch_and_post.py and set your BLOG_ID.")
    service = authenticate_blogger()
    for entry in fetch_scholarships():
        post_to_blogger(service, entry)

if __name__ == "__main__":
    main()
