#!/usr/bin/env python3
"""Turn numbered PDF and standalone video pages into a simple website.

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
    media/                         # optional: video, audio, or slideshow files
      005_Case_Introduction.mp4    # standalone video page
      020_Interview.mp4            # local video shown on the matching PDF page
      030_Final_Clue.pptx           # one slideshow file, converted by the workflow
    locks/                         # optional: answers for game-play locks
      030_Final_Clue.txt

NUMBERING
=========
Each PDF name and standalone video name starts with a three-digit number, then
_ or -, then a name. Lower numbers appear first. Leave gaps so new pages can be
added later without renaming the other files. A multi-page PDF is one website
page, with all of its PDF pages shown in order. A numbered video with no
matching PDF creates its own page. A video whose filename stem exactly matches
a PDF is shown before that PDF on the same page.

VIDEO, AUDIO, AND SLIDESHOWS
=====================
To show a local video, upload an .mp4 or .webm into media/ with the same
filename stem as its PDF. For example, 020_Interview.mp4 goes with
pdfs/020_Interview.pdf. The centered video player includes browser playback
and full-screen controls.

To make a video its own page, upload a numbered .mp4 or .webm into media/ that
does not have a PDF with the same filename stem. For example,
media/005_Case_Introduction.mp4 creates a page before pdfs/010_Home.pdf.

To show a click-through slideshow, upload one .pdf, .pptx, .ppsx, or .odp file
into media/ with the same filename stem as its matching PDF. For example,
media/030_Final_Clue.pptx goes with pdfs/030_Final_Clue.pdf. The workflow
converts PowerPoint and OpenDocument files to PDF, then builds a centered
slideshow with Previous, Next, a slide count, and a Full screen button. Slides
appear before the matching page's PDF. You do not need to make or upload
separate slide images.

Keynote .key files must first be exported as PDF or PowerPoint. MP4 videos
remain videos rather than click-through slideshows.

For externally hosted videos or audio links, make a .txt file in media with
the same name as the PDF, such as 020_Interview.txt. Put one or both lines in it:

    youtube=https://youtu.be/VIDEO_ID
    audio=https://example.org/audio/interview.mp3

YouTube stays hosted on YouTube. Direct audio links get an audio player; other
audio links appear as clickable links. Large local videos (up to the GitHub
repository's file limits) can be uploaded into the media folder.

OPTIONAL PAGE TITLE OVERRIDES
=============================
Add page_titles.csv beside title.txt to give a page a custom menu title and/or
banner title. The three-digit page number connects each row to a PDF page or
standalone video page. Blank title cells keep the title derived from its filename.

    page_number,menu_title,banner_title
    010,Executive Lunchroom - Activity,Executive Lunchroom

Edit this CSV in the GitHub website, then run Publish again to update the site.

OPTIONAL GAME COVER IMAGE
=========================
Place one image named cover.png, cover.jpg, cover.jpeg, or cover.webp beside
title.txt in that game's folder. The same image becomes the banner on every
section page, with that section's title shown over the image.

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

    background=#eff3d2
    text=#071b63
    accent=#b00078
    font=Georgia, serif

Edit styles.txt, then build or publish again. The new style is applied to that
game. The PDF artwork itself stays exactly as designed because it is shown as
an image; styles.txt changes the website around it.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
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
NUMBERED_VIDEO_RE = re.compile(r"^(\d{3})[_-](.+)$", re.IGNORECASE)
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".ogg", ".wav"}
VIDEO_EXTENSIONS = {".mp4", ".webm"}
SLIDE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
PRESENTATION_EXTENSIONS = {".pdf", ".pptx", ".ppsx", ".odp"}
COVER_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
STYLE_COLOR_KEYS = {"background", "text", "muted", "accent", "card", "border"}
STYLE_KEYS = STYLE_COLOR_KEYS | {"font"}
SAFE_FONT_RE = re.compile(r'^[A-Za-z0-9 ,"\'-]+$')
MARKER = ".mystery-site-generated"

# Style rules written into the generated website.
CSS = r"""
:root { color-scheme: light; --ink:#071b63; --muted:#344575; --teal:#0735c9;
        --paper:#eff3d2; --card:#ffffff; --line:#071b63; --coral:#b00078;
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
.game-hero { position:relative; display:flex; flex-direction:column; justify-content:center;
             width:100%; height:clamp(240px, 35vw, 460px); margin:0 auto 24px; padding:0 16px;
             background:linear-gradient(135deg,#f1f5d8,#dfe9b4); }
.hero-art, .hero-shade { position:absolute; inset:0; width:100%; height:100%; }
.hero-art { object-fit:cover; }
.hero-shade { background:#071b6318; }
.hero-content { position:relative; z-index:2; width:min(960px, 100%); margin:auto;
                padding:24px 0; text-align:center; }
.hero-content h1 { display:inline-block; margin:0; padding:12px 22px; border-radius:22px;
                   color:var(--ink); background:#ffffffb8; font-size:clamp(2rem,6vw,4.5rem);
                   text-wrap:balance; }
.hero-content .lede { margin-top:12px; color:var(--ink); font-size:1.1rem; }
.hero-toolbar { position:absolute; z-index:3; inset:auto 0 0; width:100%; margin:0; padding:12px max(16px, calc((100% - 960px)/2)); }
.hero-toolbar .header-row { justify-content:flex-end; }
.hero-toolbar .crumbs { display:none; }
.pdf-page { display:block; width:100%; height:auto; margin:0 auto 18px;
            border:1px solid var(--line); background:white; box-shadow:0 4px 16px #172b3b14; }
.media-block { background:var(--card); border:1px solid var(--line); border-radius:14px;
               padding:16px; margin:16px auto; text-align:center; }
.media-block > strong { display:block; }
audio, video { display:block; width:100%; max-width:760px; margin:8px auto 0; }
.video-frame { position:relative; width:100%; max-width:900px; aspect-ratio:16/9; margin:8px auto 0; }
.video-frame iframe { position:absolute; inset:0; width:100%; height:100%; border:0; }
.controls { display:flex; gap:16px; justify-content:space-between; align-items:center; margin:20px 0; }
.button { display:inline-block; border-radius:999px; padding:10px 16px; background:var(--coral);
          color:white; text-decoration:none; font-weight:650; }
.button.secondary { background:white; color:var(--teal); border:1px solid var(--teal); }
.page-header { position:relative; }
.header-row { display:flex; align-items:center; justify-content:space-between; gap:16px; }
.header-row .crumbs { margin:0; }
.menu-toggle { display:inline-flex; align-items:center; gap:10px; padding:11px 16px;
               border:0; border-radius:18px; color:white;
               background:var(--coral); font:inherit; font-weight:750; cursor:pointer; box-shadow:0 5px 18px #071b6325; }
.menu-toggle:hover, .menu-toggle:focus-visible { outline:3px solid #b9e1df; }
.hamburger { display:grid; gap:4px; width:20px; }
.hamburger span { display:block; height:2px; border-radius:2px; background:currentColor; }
.page-menu { position:fixed; z-index:20; top:12px; right:16px; width:min(360px, calc(100vw - 32px));
             max-height:calc(100vh - 24px); max-height:calc(100dvh - 24px);
             overflow-y:auto; overscroll-behavior:contain; -webkit-overflow-scrolling:touch; padding:12px;
             border:1px solid var(--line); border-radius:14px; background:var(--card);
             box-shadow:0 12px 32px #172b3b24; }
.page-menu ol { list-style:none; margin:0; padding:0; display:grid; gap:4px; }
.page-menu a { display:block; padding:10px 12px; border-radius:8px; text-decoration:none; }
.page-menu a:hover, .page-menu a:focus-visible { outline:2px solid #b9e1df; }
.page-menu a[aria-current="page"] { color:var(--ink); background:#e6f4f2; font-weight:700; }
.slideshow { width:min(900px, 100%); margin:16px auto; padding:16px; text-align:center;
             border:1px solid var(--line); border-radius:14px; background:var(--card); }
.slide-stage { min-height:180px; display:grid; place-items:center; }
.slide-image { display:block; max-width:100%; max-height:72vh; width:auto; height:auto; object-fit:contain; }
.slide-controls { display:flex; align-items:center; justify-content:center; gap:16px; margin-top:12px; }
.slide-controls button, .slide-fullscreen { border:0; border-radius:999px; padding:9px 16px; color:white;
                 background:var(--coral); font:inherit; font-weight:700; cursor:pointer; }
.slide-count { min-width:4.5em; color:var(--ink); font-weight:700; }
.slide-fullscreen { margin-top:10px; }
.slideshow:fullscreen { width:100vw; height:100vh; margin:0; border:0; border-radius:0;
                        display:flex; flex-direction:column; justify-content:center; background:#071b63; color:white; }
.slideshow:fullscreen .slide-stage { flex:1; min-height:0; }
.slideshow:fullscreen .slide-image { max-height:calc(100vh - 150px); }
.slideshow:fullscreen .slide-count { color:white; }
.lock-box { max-width:520px; padding:22px; background:#e6f4f2; border-radius:16px; }
.lock-box label { display:block; font-weight:650; margin-bottom:8px; }
.lock-box input { width:100%; padding:12px; border:1px solid #8bb8b7; border-radius:8px; font:inherit; }
.lock-box button { margin-top:12px; padding:11px 16px; border:0; border-radius:8px;
                    color:white; background:var(--coral); font:inherit; font-weight:650; cursor:pointer; }
.lock-error { color:#b63c28; min-height:1.5em; margin:.6rem 0 0; }
[hidden] { display:none !important; }
@media (max-width:600px) {
  header { padding-top:12px; }
  .game-hero { height:clamp(235px, 58vw, 340px); margin-bottom:16px; }
  .hero-content { padding:12px 8px 68px; }
  .hero-content h1 { padding:10px 13px; border-radius:16px; font-size:clamp(1.7rem, 8vw, 2.5rem); }
  .hero-toolbar { padding:10px 14px; }
  .menu-toggle { padding:9px 12px; gap:8px; font-size:.92rem; }
  .hamburger { width:18px; }
  .page-menu { right:12px; width:min(340px, calc(100vw - 24px)); }
  .controls { flex-direction:row; gap:12px; }
  .controls > * { min-width:0; }
  .controls .button { padding:8px 13px; font-size:.95rem; }
  .slide-controls { gap:8px; }
  .slide-controls button, .slide-fullscreen { padding:8px 12px; font-size:.95rem; }
}
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
    if (open) positionMenu();
  };

  const positionMenu = () => {
    const buttonRect = button.getBoundingClientRect();
    const viewportHeight = window.visualViewport ? window.visualViewport.height : window.innerHeight;
    const availableHeight = Math.max(120, viewportHeight - 24);
    menu.style.maxHeight = `${availableHeight}px`;
    menu.style.right = `${Math.max(12, window.innerWidth - buttonRect.right)}px`;
    const menuHeight = Math.min(menu.scrollHeight, availableHeight);
    const top = Math.max(12, Math.min(buttonRect.top - 12 - menuHeight, viewportHeight - menuHeight - 12));
    menu.style.top = `${top}px`;
  };

  button.addEventListener('click', () => {
    setOpen(button.getAttribute('aria-expanded') !== 'true');
  });
  window.addEventListener('resize', () => {
    if (!menu.hidden) positionMenu();
  });
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', () => {
      if (!menu.hidden) positionMenu();
    });
  }
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

SLIDESHOW_JS = r"""
document.querySelectorAll('[data-slideshow]').forEach((show) => {
  const slides = [...show.querySelectorAll('[data-slide]')];
  const counter = show.querySelector('[data-slide-count]');
  const previous = show.querySelector('[data-slide-prev]');
  const next = show.querySelector('[data-slide-next]');
  const full = show.querySelector('[data-slide-fullscreen]');
  let current = 0;
  const display = () => {
    slides.forEach((slide, index) => { slide.hidden = index !== current; });
    counter.textContent = `${current + 1} / ${slides.length}`;
    previous.disabled = current === 0;
    next.disabled = current === slides.length - 1;
  };
  previous.addEventListener('click', () => { if (current > 0) current--; display(); });
  next.addEventListener('click', () => { if (current < slides.length - 1) current++; display(); });
  full.addEventListener('click', async () => {
    try {
      if (!document.fullscreenElement) await show.requestFullscreen();
      else await document.exitFullscreen();
    } catch (_) { window.open(slides[current].src, '_blank', 'noopener'); }
  });
  document.addEventListener('fullscreenchange', () => {
    full.textContent = document.fullscreenElement === show ? 'Exit full screen' : 'Full screen';
  });
  display();
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
        "accent": "--coral",
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
            if path.suffix.lower() in AUDIO_EXTENSIONS | VIDEO_EXTENSIONS:
                matches.append(path)
    return sorted(matches, key=lambda p: (p.suffix.lower() not in VIDEO_EXTENSIONS, p.name.casefold()))


def find_slideshow_images(media_dir: Path, pdf_stem: str) -> list[Path]:
    """Images inside media/<exact PDF stem>/ form an ordered slideshow."""
    if not media_dir.is_dir():
        return []
    slide_dir = next(
        (path for path in media_dir.iterdir() if path.is_dir() and path.name.casefold() == pdf_stem.casefold()),
        media_dir / pdf_stem,
    )
    if not slide_dir.is_dir():
        return []
    images = [p for p in slide_dir.iterdir() if p.is_file() and p.suffix.casefold() in SLIDE_EXTENSIONS]
    return sorted(images, key=lambda p: (p.name.casefold(), p.name))


def find_matching_presentation(media_dir: Path, pdf_stem: str) -> Path | None:
    """Find one uploaded slideshow file associated with a numbered PDF page."""
    if not media_dir.is_dir():
        return None
    matches = [
        path for path in media_dir.iterdir()
        if path.is_file()
        and path.stem.casefold() == pdf_stem.casefold()
        and path.suffix.casefold() in PRESENTATION_EXTENSIONS
    ]
    if len(matches) > 1:
        names = ", ".join(path.name for path in sorted(matches, key=lambda p: p.name.casefold()))
        raise ValueError(
            f"Use only one slideshow file for {pdf_stem}; found: {names}"
        )
    return matches[0] if matches else None


def render_uploaded_slideshow(source: Path, media_out_dir: Path, slug: str, dpi: int) -> list[str]:
    """Convert an uploaded deck to PDF if needed, then render it as slide images."""
    if source.suffix.casefold() == ".pdf":
        pdf_path = source
        return build_page_images(pdf_path, media_out_dir, f"{slug}-slide", dpi)

    soffice = shutil.which("soffice")
    if not soffice:
        raise ValueError(
            f"Cannot convert {source.name}: LibreOffice is not installed. "
            "The GitHub workflow must install libreoffice-impress for .pptx, .ppsx, and .odp slideshows."
        )

    with tempfile.TemporaryDirectory(prefix="game-slideshow-") as temporary_directory:
        conversion_dir = Path(temporary_directory)
        try:
            result = subprocess.run(
                [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(conversion_dir), str(source)],
                check=False,
                capture_output=True,
                text=True,
                timeout=180,
            )
        except subprocess.TimeoutExpired as exc:
            raise ValueError(f"Converting slideshow {source.name} took longer than 3 minutes") from exc
        pdf_path = conversion_dir / f"{source.stem}.pdf"
        if result.returncode != 0 or not pdf_path.is_file():
            detail = (result.stderr or result.stdout or "No conversion details were returned.").strip()
            raise ValueError(f"Could not convert slideshow {source.name}: {detail}")
        return build_page_images(pdf_path, media_out_dir, f"{slug}-slide", dpi)


def page_title_from_stem(stem: str) -> str:
    match = NUMBERED_VIDEO_RE.match(stem)
    raw = match.group(2) if match else stem
    return re.sub(r"[_-]+", " ", raw).strip().title()


def page_title(pdf_path: Path) -> str:
    return page_title_from_stem(pdf_path.stem)


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
                        f"{csv_path}, row {line_number}: no PDF or standalone video page "
                        f"with page number {number_text} was found"
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


def find_page_records(game_dir: Path) -> list[dict]:
    """Combine PDF pages with numbered videos that have no matching PDF."""
    pdf_records = find_pdf_records(game_dir)
    media_dir = game_dir / "media"
    records = list(pdf_records)
    pdf_stems = {item["pdf"].stem.casefold() for item in pdf_records}
    used_orders = {item["order"]: item["pdf"].name for item in pdf_records}

    if media_dir.is_dir():
        for video_path in sorted(media_dir.iterdir(), key=lambda path: path.name.casefold()):
            if not video_path.is_file() or video_path.suffix.casefold() not in VIDEO_EXTENSIONS:
                continue
            # Matching videos are handled as media on their PDF page.
            if video_path.stem.casefold() in pdf_stems:
                continue

            match = NUMBERED_VIDEO_RE.fullmatch(video_path.stem)
            if not match:
                raise ValueError(
                    f"Standalone video {video_path} must start with a three-digit "
                    "page number and _ or -, for example 005_Case_Introduction.mp4"
                )
            order = int(match.group(1))
            if order in used_orders:
                raise ValueError(
                    f"Duplicate page number {order:03d} in {game_dir}: "
                    f"{used_orders[order]} and {video_path.name}"
                )
            used_orders[order] = video_path.name
            records.append({
                "order": order,
                "pdf": None,
                "video": video_path,
                "slug": slugify(video_path.stem),
            })

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
    first_page = f'{escape(records[0]["slug"])}.html'
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(game_title)}</title><meta http-equiv="refresh" content="0; url={first_page}">
<link rel="canonical" href="{first_page}"></head>
<body><p><a href="{first_page}">Open the first page</a></p></body></html>"""


def render_game_page(
    game_title: str,
    title: str,
    slug: str,
    image_names: list[str],
    media_names: list[str],
    slideshow_names: list[str],
    youtube_url: str,
    audio_url: str,
    password: str,
    previous: str | None,
    next_page: str | None,
    page_records: list[dict],
    cover_name: str | None,
    station: bool = False,
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
        elif ext in VIDEO_EXTENSIONS:
            media_html_parts.append(
                f'<section class="media-block"><strong>Watch</strong>'
                f'<video controls playsinline preload="metadata" src="media/{escape(name)}">'
                'Your browser does not support video playback.</video></section>'
            )
    if slideshow_names:
        slides = "\n".join(
            f'<img class="slide-image" data-slide src="media/{escape(name)}" '
            f'alt="Slide {number} of {len(slideshow_names)} for {escape(title)}"'
            f'{"" if number == 1 else " hidden"}>'
            for number, name in enumerate(slideshow_names, start=1)
        )
        media_html_parts.append(
            '<section class="slideshow" data-slideshow aria-label="Picture slideshow">'
            f'<div class="slide-stage">{slides}</div>'
            '<div class="slide-controls">'
            '<button type="button" data-slide-prev aria-label="Previous image">← Previous</button>'
            '<span class="slide-count" data-slide-count aria-live="polite"></span>'
            '<button type="button" data-slide-next aria-label="Next image">Next →</button>'
            '</div><button class="slide-fullscreen" type="button" data-slide-fullscreen>Full screen</button>'
            '</section>'
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
        if next_page else '<span></span>'
    )

    menu_items = "\n".join(
        f'<li><a href="{escape(item["slug"])}.html"'
        + (' aria-current="page"' if item["slug"] == slug else "")
        + f'>{escape(item["menu_title"])}</a></li>'
        for item in page_records
    )
    cover_html = f'<img class="hero-art" src="{escape(cover_name)}" alt="">' if cover_name else ""

    if station:
        station_header = (
            f'<header class="game-hero"><img class="hero-art" src="{escape(cover_name)}" alt="">'
            if cover_name else '<header class="game-hero">'
        )
        station_header += f'<div class="hero-shade"></div><div class="hero-content"><h1>{escape(title)}</h1></div></header>'
        navigation_html = ""
        asset_prefix = "../../../"
    else:
        station_header = (
            f'<header class="game-hero page-header">{cover_html}<div class="hero-shade"></div>'
            '<div class="hero-toolbar"><div class="header-row">'
            '<button class="menu-toggle" type="button" data-menu-toggle aria-expanded="false" aria-controls="page-menu" aria-label="Open page menu">'
            '<span class="hamburger" aria-hidden="true"><span></span><span></span><span></span></span><span>Explore the Case</span></button></div></div>'
            f'<nav id="page-menu" class="page-menu" aria-label="Game contents" hidden><ol>{menu_items}</ol></nav>'
            f'<div class="hero-content"><h1>{escape(title)}</h1></div></header>'
        )
        navigation_html = f'<nav class="controls" aria-label="Page navigation">{previous_link}{next_link}</nav>'
        asset_prefix = "../"

    lock_id = f"content-{slug}"
    if password:
        password_form = f"""<form class="lock-box" data-game-lock data-answer="{escape(password)}" data-content="{escape(lock_id)}">
<label for="answer">Enter the answer to open this page</label>
<input id="answer" type="text" autocomplete="off" required>
<button type="submit">Unlock page</button><p class="lock-error" role="status" aria-live="polite"></p>
</form>"""
        password_section = f'<section class="lock-prompt">{password_form}</section>'
        content_start = f'<main id="{escape(lock_id)}" hidden>'
    else:
        password_form = ""
        password_section = ""
        content_start = "<main>"

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} — {escape(game_title)}</title><link rel="stylesheet" href="{asset_prefix}site.css"><link rel="stylesheet" href="theme.css">
<script src="{asset_prefix}unlock.js" defer></script>{'' if station else f'<script src="{asset_prefix}menu.js" defer></script>'}<script src="{asset_prefix}slideshow.js" defer></script></head>
<body>{station_header}
{password_section}{content_start}
{media_html}{image_html}
{navigation_html}
</main></body></html>"""


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
    (output_dir / "slideshow.js").write_text(SLIDESHOW_JS, encoding="utf-8")


def render_root_redirect(game_slug: str, first_page_slug: str) -> str:
    target = f"{escape(game_slug)}/{escape(first_page_slug)}.html"
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="0; url={target}"><link rel="canonical" href="{target}"><title>Opening game</title></head>
<body><p><a href="{target}">Open the first page</a></p></body></html>'''


HOST_CSS = r"""
body { margin:0; background:#eff3d2; color:#071b63; font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }
main { width:min(1050px, calc(100% - 32px)); margin:28px auto 60px; }
h1 { line-height:1.15; }
.muted { color:#435477; }
.panel, .team-card { background:white; border:1px solid #9ba8c3; border-radius:14px; padding:18px; margin:16px 0; }
label { font-weight:650; display:block; margin:8px 0; }
input, select, button { font:inherit; padding:10px 12px; border:1px solid #7483a4; border-radius:8px; }
button { background:#b00078; color:white; border:0; font-weight:700; cursor:pointer; }
button.secondary { color:#0735c9; background:white; border:1px solid #0735c9; }
button:disabled { opacity:.55; cursor:not-allowed; }
a { color:#0735c9; }
.table-wrap { overflow-x:auto; }
table { width:100%; border-collapse:collapse; background:white; }
th, td { text-align:left; padding:12px; border-bottom:1px solid #d3d9e3; vertical-align:top; }
.completed { color:#a40000; text-decoration:line-through; text-decoration-color:#d00000; text-decoration-thickness:2px; margin-right:12px; }
.current { font-weight:700; margin-right:12px; }
.team-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:12px; }
.team-card { margin:0; }
.team-card h3 { margin-top:0; }
.share-menu { display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }
.empty { color:#52617d; }
[hidden] { display:none !important; }
"""


def render_host_hub(games: list[dict]) -> str:
    links = "\n".join(
        f'<li><a href="{escape(game["slug"])}/index.html">{escape(game["title"])}</a> '
        f'<span class="muted">({len(game["pages"])} stations)</span></li>'
        for game in games
    )
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Mystery game host dashboard</title>
<style>{HOST_CSS}</style></head><body><main><h1>Mystery game host dashboard</h1>
<p class="muted">Choose a game to set up teams and assign single-page station links.</p>
<section class="panel"><ul>{links}</ul></section></main></body></html>'''


def render_host_dashboard(game: dict) -> str:
    manifest = [
        {"id": f'{item["order"]:03d}-{item["slug"]}', "title": item["menu_title"],
         "path": f'../../stations/{game["slug"]}/{item["slug"]}/'}
        for item in game["pages"]
    ]
    pages_json = json.dumps(manifest, ensure_ascii=False).replace("<", "\\u003c")
    game_json = json.dumps(game["slug"])
    script = r"""
const pages = PAGE_MANIFEST, storageKey = `mystery-host-v1:${GAME_SLUG}`;
const setup = document.getElementById('setup'), app = document.getElementById('dashboard');
const saved = () => { try { return JSON.parse(localStorage.getItem(storageKey) || 'null'); } catch (_) { return null; } };
let state = saved();
const save = () => localStorage.setItem(storageKey, JSON.stringify(state));
const siteUrl = (page) => new URL(page.path, location.href).href;
const esc = (value) => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pageFor = id => pages.find(page => page.id === id);
function draw() {
  setup.hidden = true; app.hidden = false;
  document.getElementById('assignments').innerHTML = `<div class="table-wrap"><table><thead><tr><th>Team</th><th>Assigned sites (completed sites are crossed out)</th></tr></thead><tbody>${state.teams.map(team => {
    const history = (team.completed || []).map(pageFor).filter(Boolean).map(page => `<a class="completed" href="${esc(siteUrl(page))}" target="_blank" rel="noopener">${esc(page.title)}</a>`).join(' ');
    const current = pageFor(team.current);
    return `<tr><th scope="row">${esc(team.name)}</th><td>${[history, current ? `<a class="current" href="${esc(siteUrl(current))}" target="_blank" rel="noopener">${esc(current.title)}</a>` : ''].filter(Boolean).join(' ') || '<span class="empty">No site assigned</span>'}</td></tr>`;
  }).join('')}</tbody></table></div>`;
  document.getElementById('teamCards').innerHTML = state.teams.map((team, i) => {
    const current = pageFor(team.current), completed = new Set(team.completed || []);
    const options = pages.filter(page => !completed.has(page.id) && page.id !== team.current).map(page => `<option value="${esc(page.id)}">${esc(page.title)}</option>`).join('');
    if (!current) return `<section class="team-card"><h3>${esc(team.name)}</h3><label for="site-${i}">Next game site</label><select id="site-${i}" ${options ? '' : 'disabled'}><option value="">Choose a site</option>${options}</select> <button type="button" data-assign="${i}" ${options ? '' : 'disabled'}>Assign site</button></section>`;
    const url = siteUrl(current), message = `Open your mystery game site: ${url}`;
    return `<section class="team-card"><h3>${esc(team.name)}</h3><p><strong>Current site:</strong> <a href="${esc(url)}" target="_blank" rel="noopener">${esc(current.title)}</a></p>
      <button class="secondary" type="button" data-complete="${i}">Mark site complete</button> <button type="button" data-share="${i}" aria-expanded="false">Share link</button>
      <div class="share-menu" id="share-${i}" hidden><a href="sms:?body=${encodeURIComponent(message)}">Text message</a><a href="mailto:?subject=${encodeURIComponent('Your mystery game site')}&body=${encodeURIComponent(message)}">Email</a><a href="https://wa.me/?text=${encodeURIComponent(message)}" target="_blank" rel="noopener">WhatsApp</a><button class="secondary" type="button" data-copy="${i}">Copy link</button></div></section>`;
  }).join('');
  app.querySelectorAll('[data-assign]').forEach(button => button.addEventListener('click', () => {
    const team = state.teams[Number(button.dataset.assign)], selected = document.getElementById(`site-${button.dataset.assign}`).value;
    if (!selected || team.current || team.completed.includes(selected)) return;
    team.current = selected; save(); draw();
  }));
  app.querySelectorAll('[data-complete]').forEach(button => button.addEventListener('click', () => {
    const team = state.teams[Number(button.dataset.complete)]; if (!team.current) return;
    team.completed.push(team.current); team.current = null; save(); draw();
  }));
  app.querySelectorAll('[data-share]').forEach(button => button.addEventListener('click', () => {
    const menu = document.getElementById(`share-${button.dataset.share}`); menu.hidden = !menu.hidden;
    button.setAttribute('aria-expanded', String(!menu.hidden));
  }));
  app.querySelectorAll('[data-copy]').forEach(button => button.addEventListener('click', async () => {
    const page = pageFor(state.teams[Number(button.dataset.copy)].current);
    try { await navigator.clipboard.writeText(siteUrl(page)); button.textContent = 'Copied'; }
    catch (_) { window.prompt('Copy this station link:', siteUrl(page)); }
  }));
}
document.getElementById('start').addEventListener('click', () => {
  const count = Number(document.getElementById('teamCount').value);
  if (!Number.isInteger(count) || count < 1 || count > 100) { alert('Enter a number from 1 to 100.'); return; }
  state = {teams:Array.from({length:count}, (_, i) => ({name:`Group ${i + 1}`, completed:[], current:null}))}; save(); draw();
});
document.getElementById('restart').addEventListener('click', () => {
  if (!confirm('Start over? This clears team assignments and completion marks saved in this browser.')) return;
  localStorage.removeItem(storageKey); state = null; app.hidden = true; setup.hidden = false;
});
if (state && Array.isArray(state.teams)) draw();
""".replace("PAGE_MANIFEST", pages_json).replace("GAME_SLUG", game_json)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{escape(game["title"])} — Host dashboard</title>
<style>{HOST_CSS}</style></head><body><main><h1>{escape(game["title"])}: host dashboard</h1>
<section id="setup" class="panel"><h2>Start a game</h2><p>Choose how many teams are playing.</p>
<label for="teamCount">Number of teams</label><input id="teamCount" type="number" min="1" max="100" value="2"> <button id="start" type="button">Initiate</button></section>
<section id="dashboard" hidden><section class="panel"><h2>Team assignments</h2><div id="assignments"></div></section>
<h2>Assign the next site</h2><p class="muted">Mark a team’s current site complete when they report back. Then assign any site that team has not completed.</p>
<div id="teamCards" class="team-grid"></div><p><button id="restart" class="secondary" type="button">Start over</button></p></section></main>
<script>{script}</script></body></html>'''


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
        records = find_page_records(game_dir)
        if not records:
            print(f"Skipping {game_dir.name}: no numbered PDFs or standalone videos found", file=sys.stderr)
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
            source_path = item["pdf"] or item["video"]
            default_title = page_title_from_stem(source_path.stem)
            custom_titles = title_overrides.get(item["order"], {})
            item["title"] = custom_titles.get("banner_title") or default_title
            item["menu_title"] = custom_titles.get("menu_title") or default_title
            item["lock_path"] = game_dir / "locks" / f"{source_path.stem}.txt"
            item["password"] = safe_read_text(item["lock_path"]) if item["lock_path"].is_file() else ""
            item["media"] = (
                find_matching_media(game_dir / "media", item["pdf"].stem)
                if item["pdf"] else [item["video"]]
            )
            item["slideshow_source"] = (
                find_matching_presentation(game_dir / "media", item["pdf"].stem)
                if item["pdf"] else None
            )
            item["slideshow"] = (
                [] if item["slideshow_source"] or not item["pdf"] else
                find_slideshow_images(game_dir / "media", item["pdf"].stem)
            )
            link_file = find_matching_link_file(game_dir / "media", source_path.stem)
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
    (output_dir / "index.html").write_text(
        render_root_redirect(games[0]["slug"], games[0]["pages"][0]["slug"]),
        encoding="utf-8",
    )
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
            item["images"] = (
                build_page_images(item["pdf"], image_dir, item["slug"], dpi)
                if item["pdf"] else []
            )
            copied_media = []
            for source in item["media"]:
                safe_name = f"{item['slug']}{source.suffix.lower()}"
                shutil.copy2(source, media_dir / safe_name)
                copied_media.append(safe_name)
            item["copied_media"] = copied_media
            copied_slides = []
            for index, source in enumerate(item["slideshow"], start=1):
                safe_name = f"{item['slug']}-slide-{index:03d}{source.suffix.lower()}"
                shutil.copy2(source, media_dir / safe_name)
                copied_slides.append(safe_name)
            if item["slideshow_source"]:
                copied_slides = render_uploaded_slideshow(
                    item["slideshow_source"], media_dir, item["slug"], dpi,
                )
            item["copied_slideshow"] = copied_slides
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
                    item["copied_media"], item["copied_slideshow"], item["youtube_url"], item["audio_url"], item["password"], previous_slug, next_slug,
                    game["pages"], cover_name,
                ),
                encoding="utf-8",
            )
            # A station copy has no game menu or previous/next links. Its media
            # is colocated so the shared URL opens only the assigned clue.
            station_id = item["slug"]
            station_out = output_dir / "stations" / game["slug"] / station_id
            station_images = station_out / "images"
            station_media = station_out / "media"
            station_images.mkdir(parents=True, exist_ok=True)
            station_media.mkdir(parents=True, exist_ok=True)
            for image_name in item["images"]:
                shutil.copy2(image_dir / image_name, station_images / image_name)
            for slide_name in item["copied_slideshow"]:
                shutil.copy2(media_dir / slide_name, station_media / slide_name)
            for media_name in item["copied_media"]:
                shutil.copy2(media_dir / media_name, station_media / media_name)
            (station_out / "theme.css").write_text(render_game_theme(game["styles"]), encoding="utf-8")
            if cover_name:
                shutil.copy2(game_out / cover_name, station_out / cover_name)
            (station_out / "index.html").write_text(
                render_game_page(
                    game["title"], item["title"], item["slug"], item["images"],
                    item["copied_media"], item["copied_slideshow"], item["youtube_url"],
                    item["audio_url"], item["password"], None, None,
                    [item], cover_name, station=True,
                ),
                encoding="utf-8",
            )

        host_out = output_dir / "host" / game["slug"]
        host_out.mkdir(parents=True, exist_ok=True)
        (host_out / "index.html").write_text(render_host_dashboard(game), encoding="utf-8")
    host_root = output_dir / "host"
    host_root.mkdir(parents=True, exist_ok=True)
    (host_root / "index.html").write_text(render_host_hub(games), encoding="utf-8")
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

    print(f"Built {count} pages from PDFs and media files for {args.output_dir.resolve()}")
    print("The output folder is ready for a separate GitHub Pages publishing workflow.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
