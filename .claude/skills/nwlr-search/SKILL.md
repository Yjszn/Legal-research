---
name: nwlr-search
description: Search the user's subscribed NWLR Online (nwlronline.com) legal case database through a logged-in browser session. Use whenever the user asks to search NWLR, look up a Nigerian law case, find cases on a subject matter, or fetch/summarise a case report from nwlronline.com.
---

# NWLR Online Search

The user has a paid subscription to https://nwlronline.com (Nigerian Weekly Law
Reports). This skill drives a real browser with a persistent logged-in profile
via `nwlr/nwlr_browser.py` so the user never has to search manually.

## Prerequisites (first use on a machine)

1. `pip install playwright && playwright install chromium`
2. Log the user in once, in a VISIBLE browser window:
   ```
   python nwlr/nwlr_browser.py login
   ```
   Tell the user a browser window has opened and ask them to log in with their
   NWLR credentials, then press Enter in the terminal. The session persists in
   `~/.nwlr_browser_profile` — never ask for their password and never store
   credentials in the repo.

## Searching

1. Run the search headlessly:
   ```
   python nwlr/nwlr_browser.py --headless search "<the user's query>"
   ```
2. The command prints result links AND saves a full snapshot of the results
   page under `nwlr/results/` (both `.html` and `.txt`). If the printed links
   look incomplete or noisy, Read the `.txt` snapshot and extract the real
   results (case names, citations like "(2023) 5 NWLR (Pt. 1234) 567", courts,
   dates) yourself.
3. Present results to the user as a clean list: case name, citation, court,
   and a one-line relevance note. Include the link for each case.

## Reading a specific case

```
python nwlr/nwlr_browser.py --headless fetch "<case URL>"
```
Then Read the saved `.txt` snapshot and summarise: facts, issues, holding,
ratio, and the exact NWLR citation. Quote key passages verbatim when the user
asks for authority they can cite.

## Self-correcting when the site structure doesn't match

The script was written WITHOUT access to the live site, so its selectors are
generic guesses. If `search` exits with "Could not find a search box" or
returns junk:

1. Read the saved `.html` snapshot to learn the actual page structure —
   find the real search form (its URL, input name) and the real result markup.
2. Fix `nwlr/nwlr_browser.py` accordingly: adjust `SEARCH_INPUT_SELECTORS`,
   pass `--search-url` for a dedicated search page, or improve
   `extract_result_links` with the site's real result selectors.
3. Re-run the search, verify the output is correct, and commit the fix so the
   next session benefits.

If a page says the session expired or shows a login wall, run the `login`
command again (visible window) and ask the user to log in.

## Boundaries

- Only automate the user's own authenticated, subscribed access. Never attempt
  to bypass the paywall, share retrieved content publicly, or bulk-download
  the database.
- Keep session data in the home-directory profile and snapshots in
  `nwlr/results/` (gitignored) — never commit either.
