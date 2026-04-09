#!/usr/bin/env python3
"""
build_blog.py — Auto-generates blog.html from blog/*.html files
================================================================
Run locally:   python build_blog.py
Run via CI:    see .github/workflows/build-blog.yml

How it works:
  1. Scans every .html file in the /blog/ folder
  2. Reads the title, description, date, tags, and read time
     from each post's <head> and post-header markup
  3. Sorts posts newest-first by date
  4. Rebuilds blog.html, replacing everything between the
     <!-- BLOG-START --> and <!-- BLOG-END --> markers

Requirements: Python 3.8+ and beautifulsoup4
  pip install beautifulsoup4
"""

import os
import re
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup

# ── Config ────────────────────────────────────────────────────
BLOG_DIR      = Path("blog")          # folder containing post HTML files
BLOG_HTML     = Path("blog.html")     # the listing page to update
START_MARKER  = "<!-- BLOG-START -->" # marker in blog.html where cards begin
END_MARKER    = "<!-- BLOG-END -->"   # marker in blog.html where cards end
# ─────────────────────────────────────────────────────────────


def parse_post(filepath: Path) -> dict | None:
    """Extract metadata from a single blog post HTML file."""
    try:
        soup = BeautifulSoup(filepath.read_text(encoding="utf-8"), "html.parser")
    except Exception as e:
        print(f"  ⚠ Could not parse {filepath.name}: {e}")
        return None

    # Title — from <title> tag, strip site name suffix
    raw_title = soup.title.string if soup.title else ""
    title = raw_title.split("|")[0].strip() if raw_title else filepath.stem

    # Description — from <meta name="description">
    desc_tag = soup.find("meta", attrs={"name": "description"})
    description = desc_tag["content"].strip() if desc_tag and desc_tag.get("content") else ""

    # Date — from .post-meta-date span
    date_tag = soup.find(class_="post-meta-date")
    date_str = date_tag.get_text(strip=True) if date_tag else ""
    try:
        date_obj = datetime.strptime(date_str, "%B %d, %Y")
    except ValueError:
        date_obj = datetime.min  # push undated posts to the bottom

    # Tags — all .post-tag spans
    tag_els = soup.find_all(class_="post-tag")
    tags = [t.get_text(strip=True) for t in tag_els]

    # Read time — from author-bar sibling text containing "min read"
    read_time = ""
    for el in soup.find_all(string=re.compile(r"\d+\s+min read")):
        read_time = el.strip()
        break

    # Slug — relative path from site root, e.g. blog/my-post.html
    slug = f"blog/{filepath.name}"

    return {
        "title":       title,
        "description": description,
        "date_str":    date_str,
        "date_obj":    date_obj,
        "tags":        tags,
        "read_time":   read_time,
        "slug":        slug,
        "filename":    filepath.name,
    }


def tag_class(tag_text: str) -> str:
    """Map a tag label to its CSS modifier class."""
    t = tag_text.lower()
    if any(w in t for w in ["data", "research", "epidem", "statistic"]):
        return "blog-tag--data"
    if any(w in t for w in ["field", "update", "advocacy", "disability", "voting", "policy"]):
        return "blog-tag--field"
    return "blog-tag--guide"


def render_card(post: dict) -> str:
    """Render a single blog-card HTML block for one post."""
    tags_html = "\n".join(
        f'            <span class="blog-tag {tag_class(t)}">{t}</span>'
        for t in post["tags"]
    )
    date_html = (
        f'\n            <span class="blog-date">{post["date_str"]}</span>'
        if post["date_str"] else ""
    )
    read_time_html = (
        f'<span class="blog-read-time">{post["read_time"]}</span>'
        if post["read_time"] else ""
    )

    return f"""
      <article class="blog-card">
        <div class="blog-card-body">
          <div class="blog-card-meta">
{tags_html}{date_html}
          </div>
          <h3><a href="{post["slug"]}">{post["title"]}</a></h3>
          <p class="blog-excerpt">{post["description"]}</p>
          <a href="{post["slug"]}" class="blog-read-more">Read more &rarr;</a>
        </div>
        <div class="blog-card-aside">
          {read_time_html}
        </div>
      </article>"""


def build():
    """Main build function."""
    print("🔍 Scanning blog/ folder...")

    if not BLOG_DIR.exists():
        print(f"  ✗ '{BLOG_DIR}' folder not found. Nothing to do.")
        return

    posts = []
    for filepath in sorted(BLOG_DIR.glob("*.html")):
        print(f"  → Parsing {filepath.name}")
        post = parse_post(filepath)
        if post:
            posts.append(post)

    if not posts:
        print("  No posts found.")
        return

    # Sort newest first
    posts.sort(key=lambda p: p["date_obj"], reverse=True)
    print(f"\n✅ Found {len(posts)} post(s), sorted newest first:")
    for p in posts:
        print(f"   {p['date_str'] or 'undated':20}  {p['title'][:60]}")

    # Build the cards block
    cards_html = "\n".join(render_card(p) for p in posts)

    # Read current blog.html
    if not BLOG_HTML.exists():
        print(f"\n✗ '{BLOG_HTML}' not found.")
        return

    content = BLOG_HTML.read_text(encoding="utf-8")

    # Find and replace between markers
    pattern = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
        re.DOTALL
    )

    if not re.search(pattern, content):
        print(f"\n✗ Could not find markers in {BLOG_HTML}.")
        print(f"  Make sure your blog.html contains exactly:")
        print(f"    {START_MARKER}")
        print(f"    {END_MARKER}")
        return

    new_content = re.sub(
        pattern,
        f"{START_MARKER}\n{cards_html}\n      {END_MARKER}",
        content
    )

    BLOG_HTML.write_text(new_content, encoding="utf-8")
    print(f"\n🎉 blog.html updated successfully with {len(posts)} post(s).")


if __name__ == "__main__":
    build()
