#!/usr/bin/env python3
import os
import requests
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ─── CONFIGURATION ────────────────────────────────────────────────────────────

BLOG_ID = "4110173004926574485"

SOURCES = [
    (
        "https://scholarship-positions.com/fully-funded-scholarships/",
        "#site-main article"
    ),
]

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
            # 1) Try to get title & link from <a> inside .entry-title
            a = item.select_one(".entry-title a")
            if a:
                title = a.get_text(strip=True)
                link  = a["href"]
            else:
                # 2) Fallback: text of .entry-title
                h = item.select_one(".entry-title")
                title = h.get_text(strip=True) if h else "No title"
                # and first <a> in article for the link
                any_a = item.find("a", href=True)
                link  = any_a["href"] if any_a else ""

            # Deadline
            d = item.select_one(".entry-meta time")
            deadline = d.get_text(strip=True) if d else ""

            out.append({
                "title":    title,
                "link":     link,
                "deadline": deadline,
                "country":  ""  # not on this listing page
            })
    return out

# ─── SIMPLE EXTRACTIVE SUMMARY ──────────────────────────────────────────────────

def summarize_entry(entry: dict) -> str:
    try:
        resp = requests.get(entry["link"], timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        content_el = soup.select_one(".entry-content") or soup.select_one("article")
        full_text  = content_el.get_text(separator=" ", strip=True)
    except Exception:
        full_text = f"{entry['title']} — {entry['link']}"

    # take first two sentences
    sentences = [s.strip() for s in full_text.replace("\n"," ").split(". ") if s]
    summary = ". ".join(sentences[:2])
    if not summary.endswith("."):
        summary += "."
    return summary

# ─── PUBLISH TO BLOGGER ────────────────────────────────────────────────────────

def post_to_blogger(service, entry: dict):
    summary = summarize_entry(entry)
    content = (
        f"<p>{summary}</p>\n"
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
    service = authenticate_blogger()
    entries = fetch_scholarships()
    if not entries:
        print("No scholarships found; nothing to post.")
        return
    for entry in entries:
        post_to_blogger(service, entry)

if __name__ == "__main__":
    main()
