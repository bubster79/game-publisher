#!/usr/bin/env python3
"""Turn numbered PDF game pages into a simple website.

START HERE
==========
You do not need to edit the Python code for normal use. Add PDFs and optional
media link files to the folders shown below, then run the script or choose
Publish in the connected GitHub Actions workflow.

FOLDER EXAMPLE
==============
games/
  museum-mystery/                 # one folder per game
    title.txt                     # optional: friendly game title
    description.txt               # optional: short welcome message
    cover.png                     # optional: shared banner image for this game's pages
    styles.txt                    # optional: colours/font for this game's site frame
    page_titles.csv               # optional: menu and banner title overrides
    pdfs/                          # required: the pages for this game
      010_Welcome.pdf
      020_Interview.pdf
      030_Final_Clue.pdf
    media/                         # optional: link files or small audio files
      020_Interview.txt            # links that go on the matching PDF page
    locks/                         # optional: answers for game-play locks
      030_Final_Clue.txt

NUMBERING
=========
Each PDF name starts with a three-digit number, then _ or -, then a name.
Example: 025_Extra_Clue.pdf. Lower numbers appear first. Leave gaps so a new
page can be added later without renaming the other PDFs. A multi-page PDF is
one website page, with all of its PDF pages shown in order.

VIDEO AND AUDIO LINKS
=====================
Make a .txt file in media with the same name as the PDF, such as
020_Interview.txt. Put one or both of these lines inside it:

    youtube=https://youtu.be/VIDEO_ID
    audio=https://example.org/audio/interview.mp3

YouTube stays hosted on YouTube. A direct audio file link gets an audio player;
other audio links appear as clickable links. Avoid putting video files in the
GitHub folders; this builder does not copy video files into the site.

OPTIONAL PAGE TITLE OVERRIDES
=============================
Add page_titles.csv beside title.txt to give a page a custom menu title and/or
banner title. The three-digit page number connects each row to its PDF. Blank
title cells keep the title derived from the PDF filename.

    page_number,menu_title,banner_title
    010,Executive Lunchroom - Activity,Executive Lunchroom

Edit this CSV in the GitHub website, then run Publish again to update the site.

OPTIONAL GAME COVER IMAGE
=========================
Place one image named cover.png, cover.jpg, cover.jpeg, or cover.webp beside
title.txt in that game's folder. The same image becomes the banner on the
contents page and every section page. The game title or section title is shown
over the banner automatically.

RUN LOCALLY (OPTIONAL)
=====================
Install the PDF tool once:  python -m pip install pymupdf
Build the site:            python build_game_site.py --games-dir games --output-dir site

The generated website goes into the site folder. The GitHub Actions workflow
can run the same build and publish it for you.

OPTIONAL GAME STYLE SETTINGS
============================
The default website colours and font are set below in CSS. To customize the
menu, headings, buttons, and page frame for one game, add styles.txt to that
game's folder. Example:

    background=#f7f8f5
    text=#203246
    accent=#087f83
    font=Georgia, serif

Edit styles.txt, then build or publish again. The new style is applied to that
game. The PDF artwork itself stays exactly as designed because it is shown as
an image; styles.txt changes the website around it.
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import shutil
import sys
import unicodedata
from pathlib import Path

try:
    import pymupdf
except ImportError as exc:
    raise SystemExit(
        "Missing dependency. Install it with: python -m pip install pymupdf"
    ) from exc

# These are the filename types the builder understands.
ORDER_RE = re.compile(r"^(\d{3})[_-](.+)\.pdf$", re.IGNORECASE)
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".ogg", ".wav"}
COVER_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
STYLE_COLOR_KEYS = {"background", "text", "muted", "accent", "card", "border"}
STYLE_KEYS = STYLE_COLOR_KEYS | {"font"}
SAFE_FONT_RE = re.compile(r'^[A-Za-z0-9 ,"\'-]+$')
MARKER = ".mystery-site-generated"

# Style rules written into the generated website.
CSS = r"""
:root { color-scheme: light; --ink:#203246; --muted:#617487; --teal:#087f83;
        --paper:#f7f8f5; --card:#ffffff; --line:#dfe6e7; --coral:#ed795c;
        --site-font:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
* { box-sizing:border-box; }
body { margin:0; background:var(--paper); color:var(--ink);
       font:16px/1.55 var(--site-font); }
header, main, footer { width:min(960px, calc(100% - 32px)); margin-inline:auto; }
header { padding:28px 0 16px; }
main { padding:8px 0 40px; }
footer { color:var(--muted); font-size:.9rem; padding:12px 0 28px; }
a { color:var(--teal); }
h1 { line-height:1.2; margin:.2rem 0 .5rem; font-size:clamp(1.8rem,4vw,2.6rem); }
h2 { font-size:1.15rem; }
.lede { color:var(--muted); margin:0; }
.crumbs { color:var(--muted); font-size:.95rem; }
.crumbs a { text-decoration:none; }
.page-list { list-style:none; padding:0; display:grid; gap:12px; }
.page-list a { display:block; padding:16px 18px; border:1px solid var(--line);
               border-radius:14px; background:var(--card); text-decoration:none; font-weight:650; }
.page-list a:hover, .page-list a:focus { outline:3px solid #b9e1df; }
.game-hero { position:relative; display:flex; flex-direction:column; justify-content:space-between;
             width:100%; height:clamp(260px, 36vw, 460px); margin:0 auto 24px; padding:0 16px;
             background:linear-gradient(135deg,#dce9e5,#71868a); }
.hero-art, .hero-shade { position:absolute; inset:0; width:100%; height:100%; }
.hero-art { object-fit:cover; }
.hero-shade { background:linear-gradient(90deg,#10233188,#10233144); }
.hero-content { position:relative; z-index:2; width:min(960px, 100%); margin:auto;
                padding:24px 0; text-align:center; }
.hero-content h1 { margin:0; color:white; font-size:clamp(2.1rem,7vw,5rem);
                   text-shadow:0 2px 12px #0009; }
.hero-content .lede { margin-top:12px; color:white; font-size:1.1rem;
                      text-shadow:0 1px 8px #000; }
.hero-toolbar { position:relative; z-index:3; width:min(960px, 100%); margin:0 auto; padding:16px 0; }
.hero-toolbar .crumbs a { display:inline-block; padding:8px 12px; border-radius:8px;
                          color:white; background:#203246c9; }
.pdf-page { display:block; width:100%; height:auto; margin:0 auto 18px;
            border:1px solid var(--line); background:white; box-shadow:0 4px 16px #172b3b14; }
.media-block { background:var(--card); border:1px solid var(--line); border-radius:14px;
               padding:16px; margin:16px 0; }
audio, video { display:block; width:100%; max-width:760px; margin-top:8px; }
.video-frame { position:relative; width:100%; aspect-ratio:16/9; margin-top:8px; }
.video-frame iframe { position:absolute; inset:0; width:100%; height:100%; border:0; }
.controls { display:flex; gap:12px; justify-content:space-between; margin:20px 0; }
.button { display:inline-block; border-radius:999px; padding:10px 16px; background:var(--teal);
          color:white; text-decoration:none; font-weight:650; }
.button.secondary { background:white; color:var(--teal); border:1px solid var(--teal); }
.page-header { position:relative; }
.header-row { display:flex; align-items:center; justify-content:space-between; gap:16px; }
.header-row .crumbs { margin:0; }
.menu-toggle { display:inline-flex; align-items:center; gap:10px; padding:9px 13px;
               border:1px solid var(--line); border-radius:10px; color:var(--ink);
               background:var(--card); font:inherit; font-weight:650; cursor:pointer; }
.menu-toggle:hover, .menu-toggle:focus-visible { outline:3px solid #b9e1df; }
.hamburger { display:grid; gap:4px; width:20px; }
.hamburger span { display:block; height:2px; border-radius:2px; background:currentColor; }
.page-menu { position:absolute; z-index:5; top:72px; right:16px; width:min(360px, calc(100% - 32px));
             max-height:min(65vh, 520px); overflow:auto; padding:12px;
             border:1px solid var(--line); border-radius:14px; background:var(--card);
             box-shadow:0 12px 32px #172b3b24; }
.page-menu ol { list-style:none; margin:0; padding:0; display:grid; gap:4px; }
.page-menu a { display:block; padding:10px 12px; border-radius:8px; text-decoration:none; }
.page-menu a:hover, .page-menu a:focus-visible { outline:2px solid #b9e1df; }
.page-menu a[aria-current="page"] { color:var(--ink); background:#e6f4f2; font-weight:700; }
.lock-box { max-width:520px; padding:22px; background:#e6f4f2; border-radius:16px; }
.lock-box label { display:block; font-weight:650; margin-bottom:8px; }
.lock-box input { width:100%; padding:12px; border:1px solid #8bb8b7; border-radius:8px; font:inherit; }
.lock-box button { margin-top:12px; padding:11px 16px; border:0; border-radius:8px;
                    color:white; background:var(--teal); font:inherit; font-weight:650; cursor:pointer; }
.lock-error { color:#b63c28; min-height:1.5em; margin:.6rem 0 0; }
[hidden] { display:none !important; }
@media (max-width:600px) { header { padding-top:20px; } .controls { flex-direction:column; } }
"""

# Small browser script for the optional game-answer puzzle lock.
UNLOCK_JS = r"""
document.querySelectorAll('[data-game-lock]').forEach((form) => {
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const entered = form.querySelector('input').value.trim().normalize('NFC').toLocaleLowerCase();
    const expected = form.dataset.answer.trim().normalize('NFC').toLocaleLowerCase();
    const content = document.getElementById(form.dataset.content);
    const error = form.querySelector('.lock-error');
    if (entered === expected) {
      content.hidden = false;
      form.hidden = true;
    } else {
      error.textContent = 'That answer did not unlock the page. Please try again.';
    }
  });
});
"""

# Small browser script for the collapsible list of pages in a game.
MENU_JS = r"""
document.querySelectorAll('[data-menu-toggle]').forEach((button) => {
  const menu = document.getElementById(button.getAttribute('aria-controls'));
  if (!menu) return;

  const setOpen = (open) => {
    menu.hidden = !open;
    button.setAttribute('aria-expanded', String(open));
    button.setAttribute('aria-label', open ? 'Close page menu' : 'Open page menu');
  };

  button.addEventListener('click', () => {
    setOpen(button.getAttribute('aria-expanded') !== 'true');
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !menu.hidden) {
      setOpen(false);
      button.focus();
    }
  });
  document.addEventListener('click', (event) => {
    if (!menu.hidden && !menu.contains(event.target) && !button.contains(event.target)) {
      setOpen(false);
    }
  });
});
"""


def slugify(value: str) -> str:
    """Return a readable, URL-safe slug."""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return value or "game"


def escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path} must be saved as UTF-8 text") from exc


def read_game_styles(game_dir: Path) -> dict[str, str]:
    """Read optional, beginner-editable colours and font from styles.txt."""
    style_path = game_dir / "styles.txt"
    if not style_path.is_file():
        return {}

    styles: dict[str, str] = {}
    for line_number, raw_line in enumerate(style_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue
        if "=" not in line:
            raise ValueError(f"{style_path}, line {line_number}: use setting=value")
        key, value = (part.strip() for part in line.split("=", 1))
        key = key.casefold()
        if key not in STYLE_KEYS:
            allowed = ", ".join(sorted(STYLE_KEYS))
            raise ValueError(f"{style_path}, line {line_number}: use one of these settings: {allowed}")
        if key in styles:
            raise ValueError(f"{style_path}, line {line_number}: {key} is listed more than once")
        if key in STYLE_COLOR_KEYS and not re.fullmatch(r"#[0-9A-Fa-f]{3}(?:[0-9A-Fa-f]{3})?", value):
            raise ValueError(f"{style_path}, line {line_number}: {key} must be a hex colour such as #203246")
        if key == "font" and (not value or not SAFE_FONT_RE.fullmatch(value)):
            raise ValueError(f"{style_path}, line {line_number}: enter a simple font list, such as Georgia, serif")
        styles[key] = value
    return styles


def render_game_theme(styles: dict[str, str]) -> str:
    """Make small CSS overrides; the normal CSS remains the default theme."""
    css_variables = {
        "background": "--paper",
        "text": "--ink",
        "muted": "--muted",
        "accent": "--teal",
        "card": "--card",
        "border": "--line",
        "font": "--site-font",
    }
    overrides = "\n".join(
        f"  {css_variables[key]}: {value};"
        for key, value in styles.items()
    )
    return f":root {{\n{overrides}\n}}\n" if overrides else ":root {}\n"


def find_matching_media(media_dir: Path, pdf_stem: str) -> list[Path]:
    """Find media files whose name before the extension matches the PDF."""
    if not media_dir.is_dir():
        return []
    matches = []
    for path in media_dir.iterdir():
        if path.is_file() and path.stem.casefold() == pdf_stem.casefold():
            if path.suffix.lower() in AUDIO_EXTENSIONS:
                matches.append(path)
    return sorted(matches, key=lambda p: (p.suffix.lower() not in AUDIO_EXTENSIONS, p.name.casefold()))


def page_title(pdf_path: Path) -> str:
    match = ORDER_RE.match(pdf_path.name)
    raw = match.group(2) if match else pdf_path.stem
    return re.sub(r"[_-]+", " ", raw).strip().title()


def read_page_title_overrides(game_dir: Path, records: list[dict]) -> dict[int, dict[str, str]]:
    """Read optional per-page menu and banner titles from page_titles.csv."""
    csv_path = game_dir / "page_titles.csv"
    if not csv_path.is_file():
        return {}

    known_pages = {item["order"] for item in records}
    overrides: dict[int, dict[str, str]] = {}
    required_columns = {"page_number", "menu_title", "banner_title"}

    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if not reader.fieldnames:
                raise ValueError(f"{csv_path} is empty; add the page_titles.csv column headings")
            reader.fieldnames = [name.strip() if name else name for name in reader.fieldnames]
            missing = required_columns - set(reader.fieldnames)
            if missing:
                raise ValueError(
                    f"{csv_path} needs these column headings: "
                    "page_number,menu_title,banner_title"
                )

            for line_number, row in enumerate(reader, start=2):
                if not row or not any((value or "").strip() for value in row.values() if isinstance(value, str)):
                    continue
                number_text = (row.get("page_number") or "").strip()
                if not re.fullmatch(r"\d{3}", number_text):
                    raise ValueError(
                        f"{csv_path}, row {line_number}: page_number must be three digits, such as 010"
                    )
                order = int(number_text)
                if order not in known_pages:
                    raise ValueError(
                        f"{csv_path}, row {line_number}: no PDF with page number {number_text} was found"
                    )
                if order in overrides:
                    raise ValueError(
                        f"{csv_path}, row {line_number}: page number {number_text} is listed more than once"
                    )
                overrides[order] = {
                    "menu_title": (row.get("menu_title") or "").strip(),
                    "banner_title": (row.get("banner_title") or "").strip(),
                }
    except UnicodeDecodeError as exc:
        raise ValueError(f"{csv_path} must be saved as UTF-8 text") from exc

    return overrides


def read_page_links(path: Path) -> dict[str, str]:
    """Read optional video/audio URLs from a matching media/*.txt file."""
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path} must be saved as UTF-8 text") from exc
    for line_number, line in enumerate(lines, start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path}, line {line_number}: use key=value, e.g. youtube=https://youtu.be/VIDEO_ID")
        key, value = (part.strip() for part in line.split("=", 1))
        key = key.casefold()
        if key not in {"youtube", "audio"}:
            raise ValueError(f"{path}, line {line_number}: supported keys are youtube and audio")
        if key in values:
            raise ValueError(f"{path}, line {line_number}: duplicate {key} entry")
        if not value.startswith("https://"):
            raise ValueError(f"{path}, line {line_number}: link must start with https://")
        values[key] = value
    return values


def youtube_embed_url(url: str, source: Path) -> str:
    """Convert a normal YouTube watch/share URL into an embed URL."""
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(url)
    host = (parsed.hostname or "").casefold()
    video_id = ""
    if host in {"youtu.be", "www.youtu.be"}:
        video_id = parsed.path.strip("/").split("/")[0]
    elif host in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtube-nocookie.com", "www.youtube-nocookie.com"}:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        else:
            parts = parsed.path.strip("/").split("/")
            if len(parts) >= 2 and parts[0] in {"embed", "shorts", "live"}:
                video_id = parts[1]
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError(f"{source}: couldn't recognize this YouTube link: {url}")
    return f"https://www.youtube-nocookie.com/embed/{video_id}"


def find_matching_link_file(media_dir: Path, page_stem: str) -> Path | None:
    path = media_dir / f"{page_stem}.txt"
    return path if path.is_file() else None


def audio_is_direct_file(url: str) -> bool:
    from urllib.parse import urlparse

    return Path(urlparse(url).path).suffix.casefold() in AUDIO_EXTENSIONS


def find_pdf_records(game_dir: Path) -> list[dict]:
    pdf_dir = game_dir / "pdfs"
    if not pdf_dir.is_dir():
        return []

    records = []
    used_orders: dict[int, str] = {}
    for pdf_path in pdf_dir.iterdir():
        if not pdf_path.is_file() or pdf_path.suffix.lower() != ".pdf":
            continue
        match = ORDER_RE.match(pdf_path.name)
        if not match:
            raise ValueError(
                f"{pdf_path} must start with a three-digit order number and _ or -, "
                "for example 025_Extra_Clue.pdf"
            )
        order = int(match.group(1))
        if order in used_orders:
            raise ValueError(
                f"Duplicate order number {order:03d} in {pdf_dir}: "
                f"{used_orders[order]} and {pdf_path.name}"
            )
        used_orders[order] = pdf_path.name
        records.append({"order": order, "pdf": pdf_path, "slug": slugify(pdf_path.stem)})

    return sorted(records, key=lambda item: item["order"])


def find_cover_image(game_dir: Path) -> Path | None:
    """Find the optional cover image beside a game's other settings files."""
    matches = sorted(
        (path for path in game_dir.iterdir()
         if path.is_file() and path.stem.casefold() == "cover"
         and path.suffix.casefold() in COVER_IMAGE_EXTENSIONS),
        key=lambda path: path.name.casefold(),
    )
    if len(matches) > 1:
        names = ", ".join(path.name for path in matches)
        raise ValueError(f"Use only one cover image in {game_dir}; found: {names}")
    return matches[0] if matches else None


def build_page_images(pdf_path: Path, image_dir: Path, stem_slug: str, dpi: int) -> list[str]:
    image_dir.mkdir(parents=True, exist_ok=True)
    images = []
    try:
        with pymupdf.open(pdf_path) as pdf:
            if pdf.page_count == 0:
                raise ValueError(f"PDF has no pages: {pdf_path}")
            for page_number, page in enumerate(pdf, start=1):
                image_name = f"{stem_slug}-{page_number:03d}.png"
                image_path = image_dir / image_name
                pixmap = page.get_pixmap(dpi=dpi, alpha=False)
                pixmap.save(image_path)
                images.append(image_name)
    except Exception as exc:
        raise ValueError(f"Could not render {pdf_path}: {exc}") from exc
    return images


def render_game_index(
    game_title: str,
    description: str,
    slug: str,
    records: list[dict],
    cover_name: str | None,
) -> str:
    items = "\n".join(
        f'<li><a href="{escape(item["slug"])}.html">{escape(item["menu_title"])}</a></li>'
        for item in records
    )
    description_html = f'<p class="lede">{escape(description)}</p>' if description else ""
    cover_html = f'<img class="hero-art" src="{escape(cover_name)}" alt="">' if cover_name else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(game_title)}</title><link rel="stylesheet" href="../site.css"><link rel="stylesheet" href="theme.css"></head>
<body><header class="game-hero">{cover_html}<div class="hero-shade"></div>
<div class="hero-content"><h1>{escape(game_title)}</h1>{description_html}</div></header>
<main><h2>Game contents</h2><ol class="page-list">{items}</ol></main>
</body></html>"""


def render_game_page(
    game_title: str,
    title: str,
    slug: str,
    image_names: list[str],
    media_names: list[str],
    youtube_url: str,
    audio_url: str,
    password: str,
    previous: str | None,
    next_page: str | None,
    page_records: list[dict],
    cover_name: str | None,
) -> str:
    image_html = "\n".join(
        f'<img class="pdf-page" src="images/{escape(name)}" '
        f'alt="Page {number} of {escape(title)}" loading="lazy">'
        for number, name in enumerate(image_names, start=1)
    )

    media_html_parts = []
    for name in media_names:
        ext = Path(name).suffix.lower()
        if ext in AUDIO_EXTENSIONS:
            media_html_parts.append(
                f'<section class="media-block"><strong>Listen</strong>'
                f'<audio controls preload="none" src="media/{escape(name)}">'
                'Your browser does not support audio playback.</audio></section>'
            )
    media_html = "\n".join(media_html_parts)
    if youtube_url:
        media_html += (
            '\n<section class="media-block"><strong>Watch</strong>'
            f'<div class="video-frame"><iframe src="{escape(youtube_url)}" '
            f'title="Video for {escape(title)}" loading="lazy" '
            'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" '
            'referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe></div></section>'
        )
    if audio_url:
        if audio_is_direct_file(audio_url):
            media_html += (
                '\n<section class="media-block"><strong>Listen</strong>'
                f'<audio controls preload="none" src="{escape(audio_url)}">'
                'Your browser does not support audio playback.</audio></section>'
            )
        else:
            media_html += (
                '\n<section class="media-block">'
                f'<a href="{escape(audio_url)}" target="_blank" rel="noopener">Open audio link</a></section>'
            )

    previous_link = (
        f'<a class="button secondary" href="{escape(previous)}.html">← Previous</a>'
        if previous else '<span></span>'
    )
    next_link = (
        f'<a class="button" href="{escape(next_page)}.html">Next →</a>'
        if next_page else '<a class="button" href="index.html">Game menu</a>'
    )

    menu_items = "\n".join(
        f'<li><a href="{escape(item["slug"])}.html"'
        + (' aria-current="page"' if item["slug"] == slug else "")
        + f'>{escape(item["menu_title"])}</a></li>'
        for item in page_records
    )
    cover_html = f'<img class="hero-art" src="{escape(cover_name)}" alt="">' if cover_name else ""

    lock_id = f"content-{slug}"
    if password:
        password_form = f"""<form class="lock-box" data-game-lock data-answer="{escape(password)}" data-content="{escape(lock_id)}">
<label for="answer">Enter the answer to open this page</label>
<input id="answer" type="text" autocomplete="off" required>
<button type="submit">Unlock page</button><p class="lock-error" role="status" aria-live="polite"></p>
</form>"""
        content_start = f'<main id="{escape(lock_id)}" hidden>'
    else:
        password_form = ""
        content_start = "<main>"

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} — {escape(game_title)}</title><link rel="stylesheet" href="../site.css"><link rel="stylesheet" href="theme.css">
<script src="../unlock.js" defer></script><script src="../menu.js" defer></script></head>
<body><header class="game-hero page-header">{cover_html}<div class="hero-shade"></div>
<div class="hero-toolbar"><div class="header-row"><p class="crumbs"><a href="index.html">Game contents</a></p>
<button class="menu-toggle" type="button" data-menu-toggle aria-expanded="false" aria-controls="page-menu" aria-label="Open page menu">
<span class="hamburger" aria-hidden="true"><span></span><span></span><span></span></span><span>Jump to</span></button></div></div>
<nav id="page-menu" class="page-menu" aria-label="Game contents" hidden><ol>{menu_items}</ol></nav>
<div class="hero-content"><h1>{escape(title)}</h1></div></header>
<main>{password_form}</main>{content_start}
{media_html}{image_html}
<nav class="controls" aria-label="Page navigation">{previous_link}{next_link}</nav>
</main><footer><a href="index.html">Return to game menu</a></footer></body></html>"""


def prepare_output(output_dir: Path) -> None:
    if output_dir.exists():
        if not output_dir.is_dir():
            raise ValueError(f"Output path is not a directory: {output_dir}")
        marker = output_dir / MARKER
        if any(output_dir.iterdir()) and not marker.is_file():
            raise ValueError(
                f"Refusing to replace non-generated output folder: {output_dir}. "
                f"Choose an empty folder or one previously built by this script."
            )
        if marker.is_file():
            shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / MARKER).write_text("Generated by build_game_site.py\n", encoding="utf-8")
    (output_dir / "site.css").write_text(CSS, encoding="utf-8")
    (output_dir / "unlock.js").write_text(UNLOCK_JS, encoding="utf-8")
    (output_dir / "menu.js").write_text(MENU_JS, encoding="utf-8")


def build_site(games_dir: Path, output_dir: Path, dpi: int) -> int:
    """Read the game folders, make website pages, and return the page count."""
    if not games_dir.is_dir():
        raise ValueError(f"Games folder does not exist: {games_dir}")

    game_dirs = sorted((p for p in games_dir.iterdir() if p.is_dir()), key=lambda p: p.name.casefold())
    if not game_dirs:
        raise ValueError(f"No game folders found in {games_dir}")

    # Check the input first so an old generated website is kept if there is a
    # naming or file problem. The script replaces only its own marked output.
    games = []
    seen_slugs = set()
    for game_dir in game_dirs:
        records = find_pdf_records(game_dir)
        if not records:
            print(f"Skipping {game_dir.name}: no PDFs found in its pdfs folder", file=sys.stderr)
            continue
        game_slug = slugify(game_dir.name)
        if game_slug in seen_slugs:
            raise ValueError(f"Two game folder names produce the same website address: {game_slug}")
        seen_slugs.add(game_slug)
        game_title = game_dir.name.replace("_", " ").replace("-", " ").title()
        title_file = game_dir / "title.txt"
        if title_file.is_file():
            custom_title = safe_read_text(title_file)
            if custom_title:
                game_title = custom_title
        description_file = game_dir / "description.txt"
        description = safe_read_text(description_file) if description_file.is_file() else ""
        cover_image = find_cover_image(game_dir)
        styles = read_game_styles(game_dir)
        pages = []
        title_overrides = read_page_title_overrides(game_dir, records)
        for item in records:
            default_title = page_title(item["pdf"])
            custom_titles = title_overrides.get(item["order"], {})
            item["title"] = custom_titles.get("banner_title") or default_title
            item["menu_title"] = custom_titles.get("menu_title") or default_title
            item["lock_path"] = game_dir / "locks" / f"{item['pdf'].stem}.txt"
            item["password"] = safe_read_text(item["lock_path"]) if item["lock_path"].is_file() else ""
            item["media"] = find_matching_media(game_dir / "media", item["pdf"].stem)
            link_file = find_matching_link_file(game_dir / "media", item["pdf"].stem)
            item["links"] = read_page_links(link_file) if link_file else {}
            item["youtube_url"] = youtube_embed_url(item["links"]["youtube"], link_file) if "youtube" in item["links"] else ""
            item["audio_url"] = item["links"].get("audio", "")
            pages.append(item)
        games.append({"dir": game_dir, "slug": game_slug, "title": game_title,
                      "description": description, "cover": cover_image,
                      "styles": styles, "pages": pages})

    if not games:
        raise ValueError("No game folders with PDFs were found.")

    # All input folders are valid, so it is now safe to rebuild the output.
    prepare_output(output_dir)
    for game in games:
        game_out = output_dir / game["slug"]
        image_dir = game_out / "images"
        media_dir = game_out / "media"
        image_dir.mkdir(parents=True, exist_ok=True)
        media_dir.mkdir(parents=True, exist_ok=True)
        (game_out / "theme.css").write_text(render_game_theme(game["styles"]), encoding="utf-8")
        cover_name = None
        if game["cover"]:
            cover_name = game["cover"].name
            shutil.copy2(game["cover"], game_out / cover_name)

        page_titles = []
        # Turn each PDF page into an image the browser can display.
        for item in game["pages"]:
            item["images"] = build_page_images(item["pdf"], image_dir, item["slug"], dpi)
            copied_media = []
            for source in item["media"]:
                safe_name = f"{item['slug']}{source.suffix.lower()}"
                shutil.copy2(source, media_dir / safe_name)
                copied_media.append(safe_name)
            item["copied_media"] = copied_media
            page_titles.append((item["slug"], item["title"]))

        (game_out / "index.html").write_text(
            render_game_index(
                game["title"], game["description"], game["slug"], game["pages"], cover_name,
            ),
            encoding="utf-8",
        )
        for index, item in enumerate(game["pages"]):
            previous_slug = game["pages"][index - 1]["slug"] if index > 0 else None
            next_slug = game["pages"][index + 1]["slug"] if index + 1 < len(game["pages"]) else None
            (game_out / f"{item['slug']}.html").write_text(
                render_game_page(
                    game["title"], item["title"], item["slug"], item["images"],
                    item["copied_media"], item["youtube_url"], item["audio_url"], item["password"], previous_slug, next_slug,
                    game["pages"], cover_name,
                ),
                encoding="utf-8",
            )
    return sum(len(game["pages"]) for game in games)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate static mystery-game pages from numbered PDFs.")
    parser.add_argument("--games-dir", type=Path, default=Path("games"), help="Folder containing one folder per game (default: games)")
    parser.add_argument("--output-dir", type=Path, default=Path("site"), help="Generated site folder (default: site)")
    parser.add_argument("--dpi", type=int, default=150, help="PDF render resolution (default: 150 DPI)")
    args = parser.parse_args()

    if args.dpi < 72 or args.dpi > 300:
        parser.error("--dpi must be between 72 and 300")

    try:
        count = build_site(args.games_dir.resolve(), args.output_dir.resolve(), args.dpi)
    except (OSError, ValueError) as exc:
        print(f"Build stopped: {exc}", file=sys.stderr)
        return 1

    print(f"Built {count} pages from PDFs and media links for {args.output_dir.resolve()}")
    print("The output folder is ready for a separate GitHub Pages publishing workflow.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
