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
  4. Collects all unique tags across posts
  5. Rebuilds blog.html, replacing:
     - Tag filter buttons between <!-- FILTERS-START --> / <!-- FILTERS-END -->
     - Blog cards between <!-- BLOG-START --> / <!-- BLOG-END -->
     - Filter script between <!-- SCRIPT-START --> / <!-- SCRIPT-END -->

Requirements: Python 3.8+ and beautifulsoup4
  pip install beautifulsoup4
"""

import os
import re
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from collections import Counter

# ── Config ────────────────────────────────────────────────────
BLOG_DIR      = Path("blog")          # folder containing post HTML files
BLOG_HTML     = Path("blog.html")     # the listing page to update
START_MARKER  = "<!-- BLOG-START -->"
END_MARKER    = "<!-- BLOG-END -->"
FILTER_START  = "<!-- FILTERS-START -->"
FILTER_END    = "<!-- FILTERS-END -->"
SCRIPT_START  = "<!-- SCRIPT-START -->"
SCRIPT_END    = "<!-- SCRIPT-END -->"
# ─────────────────────────────────────────────────────────────


def parse_post(filepath: Path) -> dict | None:
    """Extract metadata from a single blog post HTML file."""
    try:
        soup = BeautifulSoup(filepath.read_text(encoding="utf-8"), "html.parser")
    except Exception as e:
        print(f"  ⚠ Could not parse {filepath.name}: {e}")
        return None

    # Skip the template file
    if filepath.name == "post-template.html":
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

    # Tags — from .post-footer-tag spans (the full tag list at the bottom of each post)
    footer_tag_els = soup.find_all(class_="post-footer-tag")
    tags = [t.get_text(strip=True) for t in footer_tag_els]

    # If no footer tags found, fall back to header .post-tag spans
    if not tags:
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
    if any(w in t for w in ["data", "research", "epidem", "statistic", "autism", "mental health", "medicaid"]):
        return "blog-tag--data"
    if any(w in t for w in ["field", "update", "advocacy", "disability", "voting", "policy",
                             "rights", "equity", "florida", "employment"]):
        return "blog-tag--field"
    return "blog-tag--guide"


def render_card(post: dict) -> str:
    """Render a single blog-card HTML block for one post."""
    # Show only the first 2 tags on the card to keep it clean
    display_tags = post["tags"][:2]
    tags_html = "\n".join(
        f'            <span class="blog-tag {tag_class(t)}" data-filter-tag="{t}">{t}</span>'
        for t in display_tags
    )
    date_html = (
        f'\n            <span class="blog-date">{post["date_str"]}</span>'
        if post["date_str"] else ""
    )
    read_time_html = (
        f'<span class="blog-read-time">{post["read_time"]}</span>'
        if post["read_time"] else ""
    )

    # All tags go in data-tags attribute for filtering
    tags_attr = ",".join(post["tags"])

    return f"""
      <article class="blog-card" data-tags="{tags_attr}">
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


def render_filters(all_tags: list[str]) -> str:
    """Render the filter button bar from all unique tags, sorted by frequency."""
    tag_counts = Counter(all_tags)
    sorted_tags = [tag for tag, _ in tag_counts.most_common()]

    buttons = ['      <button class="filter-btn active" data-tag="all">All Posts</button>']
    for tag in sorted_tags:
        buttons.append(f'      <button class="filter-btn" data-tag="{tag}">{tag}</button>')

    return "\n".join(buttons)


def render_filter_script() -> str:
    """Render the JavaScript that handles tag filtering."""
    return """    <script>
    document.addEventListener('DOMContentLoaded', () => {
      const filterBtns = document.querySelectorAll('.filter-btn[data-tag]');
      const tagBtns = document.querySelectorAll('.blog-tag[data-filter-tag]');
      const cards = document.querySelectorAll('.blog-card[data-tags]');

      function filterByTag(tag) {
        // Update active button
        filterBtns.forEach(b => b.classList.toggle('active', b.dataset.tag === tag));

        // Show/hide cards with animation
        cards.forEach(card => {
          const cardTags = card.dataset.tags.split(',');
          if (tag === 'all' || cardTags.includes(tag)) {
            card.style.display = '';
            card.style.opacity = '1';
          } else {
            card.style.display = 'none';
            card.style.opacity = '0';
          }
        });
      }

      // Filter bar button clicks
      filterBtns.forEach(btn => {
        btn.addEventListener('click', () => filterByTag(btn.dataset.tag));
      });

      // Inline tag clicks on cards
      tagBtns.forEach(btn => {
        btn.style.cursor = 'pointer';
        btn.addEventListener('click', (e) => {
          e.preventDefault();
          filterByTag(btn.dataset.filterTag);
          document.querySelector('.blog-filters').scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
      });
    });
    </script>"""


def replace_between_markers(content: str, start: str, end: str, new_inner: str) -> str:
    """Replace content between two markers, keeping the markers in place."""
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    if not re.search(pattern, content):
        print(f"  ⚠ Markers {start} / {end} not found — skipping.")
        return content
    return re.sub(pattern, f"{start}\n{new_inner}\n      {end}", content)


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

    # Collect all tags across all posts
    all_tags = []
    for p in posts:
        all_tags.extend(p["tags"])
    unique_tags = list(dict.fromkeys(all_tags))
    print(f"\n🏷  Found {len(unique_tags)} unique tag(s): {', '.join(unique_tags)}")

    # Build HTML blocks
    cards_html = "\n".join(render_card(p) for p in posts)
    filters_html = render_filters(all_tags)
    script_html = render_filter_script()

    # Read current blog.html
    if not BLOG_HTML.exists():
        print(f"\n✗ '{BLOG_HTML}' not found.")
        return

    content = BLOG_HTML.read_text(encoding="utf-8")

    # Replace cards
    content = replace_between_markers(content, START_MARKER, END_MARKER, cards_html)

    # Replace filters
    content = replace_between_markers(content, FILTER_START, FILTER_END, filters_html)

    # Replace script
    content = replace_between_markers(content, SCRIPT_START, SCRIPT_END, script_html)

    BLOG_HTML.write_text(content, encoding="utf-8")
    print(f"\n🎉 blog.html updated successfully with {len(posts)} post(s) and {len(unique_tags)} tag(s).")


if __name__ == "__main__":
    build()
