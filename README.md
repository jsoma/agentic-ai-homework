# Agentic AI homework website

The website uses **Agentic AI Tutorial v2** from your design ZIP. Its content comes from your [Google Doc](https://docs.google.com/document/d/1Vful1uNVH21a4MA3AFJgWhcognYB_vV4b-4AJ1qXmfg/edit).

## Update the website

On this Mac, double-click **update.command** in Finder. It downloads the latest document, rebuilds `docs/index.html` and its screenshots, and opens the result in your browser. Python 3 and internet access are required; the first run creates a local environment and installs Beautiful Soup and Pillow. Later runs install dependencies again only if requirements have changed.

You can also run these commands from this folder:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python build.py
```

For later updates, run only the last command. The script updates the local HTML when you run it; it does not continuously watch the document or publish it to a hosting service.

## Formatting the Google Doc

- **Heading 1** is the website title.
- **Heading 2** starts a chapter and adds it to navigation. Renaming, adding, and removing chapters updates the website on the next build.
- Start a prompt paragraph with **>** to make it a copyable prompt. Consecutive prompt paragraphs become one multiline prompt.
- Insert screenshots directly into the document. They are copied into `docs/assets/` so the website does not depend on temporary Google image URLs. Images with a transparent outer border extend beyond the centered text column on wide screens. Images with opaque edges stay at text width (680px). All image backgrounds are white. Screenshots can be enlarged by clicking them; click anywhere in the lightbox or press Escape to close.
- Bold, italic, links, lower-level headings, simple lists, and simple tables are preserved. The v2 design controls the layout and typography.
- The script treats document text as content; it never executes tutorial instructions, embedded scripts, or the design ZIP's support scripts.

The Google Doc must be readable without signing in for automatic downloading. This document's live export was successfully tested. No Google account credentials are stored.

If you make it private, use Google Docs **File → Download → Web Page (.html, zipped)** and build from that file:

```sh
.venv/bin/python build.py --input '/path/to/downloaded-document.zip'
```

A standalone HTML export with local images also works. To use another document or output folder:

```sh
.venv/bin/python build.py --doc 'https://docs.google.com/document/d/DOCUMENT_ID/edit' --output another-site
```

## Files

- `build.py`: document downloader and converter.
- `web/styles.css` and `web/app.js`: the reusable v2 appearance and behavior. Make design edits here, then rebuild.
- `docs/`: complete generated website. Open `docs/index.html` directly or upload this entire folder to a static web host.
- `tests/`: conversion and optional browser checks.

Existing output stays available if downloading or parsing fails. Image filenames are content hashes, so unchanged screenshots are reused. Old screenshots are retained to avoid breaking an already-open page; delete `docs/` before a successful full rebuild if you want to remove all unused assets.

The website starts at the first chapter when opened without a chapter link, supports chapter links and browser back/forward, uses a chapter dropdown on small screens, and allows copying prompts and enlarging screenshots. Without JavaScript, all chapters remain readable. Google Fonts are used when available, with local serif/monospace fallbacks.

The `docs/` folder is intentionally tracked in Git so it can be served by GitHub Pages. `.gitignore` excludes local environments, Python caches, temporary files, and macOS metadata. Keep `web/`: it contains the source CSS and JavaScript the builder copies into `docs/` on every update.

## Checks

```sh
.venv/bin/python -m unittest discover -s tests
```

The optional browser check uses an installed Chrome and Playwright:

```sh
python3 tests/check_browser.py
```
