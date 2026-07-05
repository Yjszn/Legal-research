"""
NWLR Online browser helper for the Legal Research project.

Drives a real Chromium browser against https://nwlronline.com using a
persistent browser profile, so you log in ONCE (in a visible window) and the
session cookies are remembered for every later search.

Commands:
    python nwlr/nwlr_browser.py login
        Opens a visible browser at NWLR Online. Log in manually, then press
        Enter in the terminal. Your session is saved in the profile directory.

    python nwlr/nwlr_browser.py status
        Opens the site and reports whether you appear to be logged in.

    python nwlr/nwlr_browser.py search "fundamental rights enforcement"
        Runs a search on the site, prints the result links, and saves a full
        snapshot (HTML + text) of the results page under nwlr/results/.

    python nwlr/nwlr_browser.py fetch "https://nwlronline.com/some/case"
        Opens any page within the logged-in session and saves a snapshot of it
        for reading/summarising.

Options:
    --headless      Run without a visible window (not usable for `login`).
    --search-url    Override the page where the search box lives.

The profile (cookies, login session) lives in ~/.nwlr_browser_profile and is
never part of the repository. Snapshots go to nwlr/results/ (gitignored).
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    print(
        "Playwright is not installed. Run:\n"
        "  pip install playwright && playwright install chromium",
        file=sys.stderr,
    )
    sys.exit(2)

BASE_URL = os.environ.get("NWLR_BASE_URL", "https://nwlronline.com")
PROFILE_DIR = Path.home() / ".nwlr_browser_profile"
RESULTS_DIR = Path(__file__).resolve().parent / "results"

# Tried in order until one matches a visible element on the page.
SEARCH_INPUT_SELECTORS = [
    "input[type='search']",
    "input[name='q']",
    "input[name='s']",
    "input[name='query']",
    "input[name*='search' i]",
    "input[id*='search' i]",
    "input[placeholder*='search' i]",
    "input[aria-label*='search' i]",
]

# Text of links/buttons that suggest the user is logged in / logged out.
LOGGED_IN_MARKERS = ["logout", "log out", "sign out", "my account", "dashboard", "profile"]
LOGGED_OUT_MARKERS = ["login", "log in", "sign in", "subscribe"]


def launch_context(p, headless: bool):
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    kwargs = {"headless": headless, "viewport": {"width": 1400, "height": 900}}
    try:
        return p.chromium.launch_persistent_context(str(PROFILE_DIR), **kwargs)
    except Exception:
        # Playwright's own browser download is missing/mismatched — fall back
        # to a system Chromium if one is available.
        fallback = os.environ.get("NWLR_CHROMIUM_PATH") or "/opt/pw-browsers/chromium"
        if Path(fallback).exists():
            return p.chromium.launch_persistent_context(
                str(PROFILE_DIR), executable_path=fallback, **kwargs
            )
        raise


def slugify(text: str, max_len: int = 60) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return slug[:max_len] or "page"


def save_snapshot(page, label: str) -> tuple[Path, Path]:
    """Save the current page as HTML and plain text; return both paths."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    base = RESULTS_DIR / f"{stamp}-{slugify(label)}"
    html_path = base.with_suffix(".html")
    text_path = base.with_suffix(".txt")
    html_path.write_text(page.content(), encoding="utf-8")
    text_path.write_text(page.inner_text("body"), encoding="utf-8")
    return html_path, text_path


def page_login_state(page) -> str:
    """Best-effort guess: 'logged_in', 'logged_out', or 'unknown'."""
    try:
        body = page.inner_text("body").lower()
    except Exception:
        return "unknown"
    if any(m in body for m in LOGGED_IN_MARKERS):
        return "logged_in"
    if any(m in body for m in LOGGED_OUT_MARKERS):
        return "logged_out"
    return "unknown"


def find_search_input(page):
    for selector in SEARCH_INPUT_SELECTORS:
        locator = page.locator(selector).first
        try:
            if locator.count() and locator.is_visible():
                return locator, selector
        except Exception:
            continue
    return None, None


def extract_result_links(page, limit: int = 30) -> list[dict]:
    """Collect substantial links from the page — likely case-report results."""
    links = page.eval_on_selector_all(
        "a[href]",
        """els => els.map(a => ({
            text: (a.innerText || '').trim().replace(/\\s+/g, ' '),
            href: a.href,
        }))""",
    )
    seen = set()
    results = []
    for link in links:
        text, href = link["text"], link["href"]
        if len(text) < 15 or href in seen:
            continue
        if not href.startswith(BASE_URL):
            continue
        seen.add(href)
        results.append(link)
        if len(results) >= limit:
            break
    return results


def cmd_login(args) -> int:
    if args.headless:
        print("`login` needs a visible browser window; drop --headless.", file=sys.stderr)
        return 2
    with sync_playwright() as p:
        context = launch_context(p, headless=False)
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(BASE_URL, wait_until="domcontentloaded")
        print(f"A browser window is open at {BASE_URL}.")
        print("Log in with your NWLR subscription credentials in that window.")
        input("When you are fully logged in, press Enter here to save the session... ")
        state = page_login_state(page)
        context.close()
        print(f"Session saved to {PROFILE_DIR} (login state detected: {state}).")
        print("Future searches will reuse this session automatically.")
    return 0


def cmd_status(args) -> int:
    with sync_playwright() as p:
        context = launch_context(p, headless=args.headless)
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(BASE_URL, wait_until="domcontentloaded")
        state = page_login_state(page)
        title = page.title()
        html_path, text_path = save_snapshot(page, "status-home")
        context.close()
    print(f"Title      : {title}")
    print(f"Login state: {state}")
    print(f"Snapshot   : {html_path}")
    print(f"Text       : {text_path}")
    return 0


def cmd_search(args) -> int:
    with sync_playwright() as p:
        context = launch_context(p, headless=args.headless)
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(args.search_url or BASE_URL, wait_until="domcontentloaded")

        state = page_login_state(page)
        if state == "logged_out":
            print(
                "WARNING: you look logged OUT. Run `python nwlr/nwlr_browser.py login` "
                "first; results may be limited.",
                file=sys.stderr,
            )

        locator, selector = find_search_input(page)
        if locator is None:
            html_path, text_path = save_snapshot(page, "no-search-box")
            context.close()
            print("Could not find a search box on the page.", file=sys.stderr)
            print(f"Page snapshot saved for inspection:\n  {html_path}\n  {text_path}", file=sys.stderr)
            print(
                "Inspect the snapshot to find the right search page/selector, then "
                "retry with --search-url or update SEARCH_INPUT_SELECTORS.",
                file=sys.stderr,
            )
            return 3

        locator.click()
        locator.fill(args.query)
        locator.press("Enter")
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass  # some sites never go idle; scrape whatever is rendered
        time.sleep(1.5)

        results = extract_result_links(page)
        html_path, text_path = save_snapshot(page, f"search-{args.query}")
        context.close()

    print(f"Search     : {args.query}")
    print(f"Search box : {selector}")
    print(f"Snapshot   : {html_path}")
    print(f"Text       : {text_path}")
    print(f"Links found: {len(results)}")
    for i, r in enumerate(results, 1):
        print(f"{i:2}. {r['text']}\n    {r['href']}")
    if not results:
        print(
            "No result links extracted — read the snapshot files above; the "
            "results may use a structure this generic extractor missed."
        )
    return 0


def cmd_fetch(args) -> int:
    with sync_playwright() as p:
        context = launch_context(p, headless=args.headless)
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(args.url, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass
        title = page.title()
        html_path, text_path = save_snapshot(page, title or args.url)
        context.close()
    print(f"Fetched  : {args.url}")
    print(f"Title    : {title}")
    print(f"Snapshot : {html_path}")
    print(f"Text     : {text_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="NWLR Online browser helper")
    parser.add_argument("--headless", action="store_true", help="run without a visible window")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("login", help="open a visible browser to log in once")
    sub.add_parser("status", help="check whether the saved session is logged in")

    p_search = sub.add_parser("search", help="run a search and extract result links")
    p_search.add_argument("query", help="search terms, e.g. a case name or subject matter")
    p_search.add_argument("--search-url", default=None, help="page where the search box lives")

    p_fetch = sub.add_parser("fetch", help="open a page in the logged-in session and snapshot it")
    p_fetch.add_argument("url", help="full URL of the page to fetch")

    args = parser.parse_args()
    return {
        "login": cmd_login,
        "status": cmd_status,
        "search": cmd_search,
        "fetch": cmd_fetch,
    }[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
