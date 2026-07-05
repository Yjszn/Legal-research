# NWLR Online search automation

Search your subscribed [NWLR Online](https://nwlronline.com) account from
Claude without doing it manually each time. A real Chromium browser runs with
a **persistent profile**, so you log in once and every later search reuses
that session.

## One-time setup (on your own computer)

```bash
pip install playwright
playwright install chromium
python nwlr/nwlr_browser.py login   # a browser opens — log in, then press Enter
```

Your session is stored in `~/.nwlr_browser_profile` on your machine only.
No password is ever stored in this repository.

## Daily use

Open this repo in Claude Code (desktop app / Cowork) and just ask, e.g.:

> Search NWLR for cases on fundamental rights enforcement

Claude uses the `nwlr-search` skill, which runs:

```bash
python nwlr/nwlr_browser.py --headless search "fundamental rights enforcement"
python nwlr/nwlr_browser.py --headless fetch "<case url>"   # to read a case
python nwlr/nwlr_browser.py status                          # check login state
```

Search results and fetched case pages are snapshotted to `nwlr/results/`
(gitignored) so Claude can read the full content and summarise it for you.

## Notes

- If the session expires, run the `login` command again.
- The script's selectors were written without access to the live site; the
  skill instructs Claude to inspect the saved page snapshot and fix the
  selectors on first use if the site's structure differs. See
  `.claude/skills/nwlr-search/SKILL.md`.
- This tooling is for your own authenticated, subscribed access only.
