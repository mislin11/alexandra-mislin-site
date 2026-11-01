# Alexandra Mislin — portable website

This is a local, GitHub-ready rebuild of Alexandra's personal website. It keeps the white layout, narrow uppercase name, quiet navigation, portrait, text columns and WorkWell Diplomacy article layout close to the verified Squarespace screenshots.

**Live website: [mislin11.github.io/alexandra-mislin-site](https://mislin11.github.io/alexandra-mislin-site/).** [Source repository](https://github.com/mislin11/alexandra-mislin-site). The custom domain has not been connected yet. The original backup remains separate and unchanged.

## Open your editor on this Mac

Double-click **Open Website Editor.app** inside this folder. Keep the app in this folder; it uses the website files beside it. It opens your browser and starts the private editor automatically. No Terminal, account, package installation or paid service is needed on this Mac (Python 3.9+ is already available).

1. Choose **Pages**, **News**, **Blog** or **CV**.
2. Change text using the normal form and formatting buttons.
3. Click **Save & Preview**. The local website rebuilds and the preview refreshes automatically.

The editor normally opens at **http://127.0.0.1:8767/editor/**. If that port is in use, the app chooses another local port and opens the right address. Reopening the app reuses this project's running editor. Closing the browser does not delete or stop the local server; reopen the app to return.

**Saving stays on this Mac. It does not publish, push to GitHub or update Squarespace.** Publishing is a separate step: commits to the GitHub repository’s `main` branch run the checked Pages build. The local editor does not upload or commit files. The existing view-only preview at port 8766 can continue alongside the editor.

There is a rich text toolbar for paragraphs, headings, bold, italic, lists and links; title, publication date and summary fields for articles; and a PDF chooser for replacing the CV. Original article addresses stay stable. New articles begin as private drafts. Every successful save keeps a recoverable previous version in **History**; **Cancel changes** discards only unsaved edits. Browser draft recovery helps if a tab reloads before saving.

See [the simple editing guide](docs/EDITING.md). This is a local content editor. New page layouts, menus and uploading new images still need a source update; existing article listing images can be selected. It does not provide remote/mobile-device access, user accounts, automatic publishing or cloud synchronization.

For technical maintenance only, the dependency-free commands remain:

```sh
python3 tools/build.py
python3 tools/check.py
python3 tools/serve.py
```

The built static website is in `dist/`. Do not edit it directly: builds replace it. Keep the editable `content/`, `public/`, `tools/`, `editor/` and app together. The private `.local-editor/` directory holds local save history and is excluded from Git, archives and the hosting container. Back up your working project folder separately if you need that history retained elsewhere.

## Publishing and portability

This repository holds the editable source. `.github/workflows/pages.yml` builds it with Python and checks the current links and assets, then publishes only the generated `dist/` folder to GitHub Pages. The local editor, its write service and its private history are excluded from the public website runtime.

After making and previewing local edits, ask for help publishing the selected changes to GitHub. Do not commit private drafts, `.local-editor/`, backups or account information: repository source and commit history are public. The editor's draft checkbox controls local preview/build inclusion and does not make GitHub source private.

The standard-library builder remains portable to other static hosts. It needs no packages, database or paid build service. The optional container recipe remains available but is not used for GitHub Pages. No Railway service or costs were created. Domain configuration is a separate coordinated step.

## What was preserved and what needs review

All nine personal blog posts retain their original titles, publication timestamps and path stems. One promotional closing paragraph was removed at the owner’s request; the academic article text remains. Research, teaching, press, the complete homepage news archive and contact information were imported. Both `/workwell-diplomacy` (landing page) and `/workwelldiplomacy/...` (collection and article routes) remain distinct. Category/tag routes, query-offset pagination, `/home`, and the legacy hospital PDF route are covered. `/read-me-om` was a Squarespace template instruction page rather than personal editorial content; the new route redirects home and its original stays in the unchanged backup.

- Fonts are self-hosted **Source Sans 3 and Oswald**, with bundled open font licenses. Oswald replaces licensed DIN Condensed Web, so the title lettering is close rather than identical. No Typekit font files or Squarespace runtime are shipped.
- The unknown-rights question-mark stock photo and publisher screenshot collage are omitted. Article text and press links remain; the optional article thumbnail is a neutral text panel. They can be restored if appropriate rights are confirmed. Other imported images retain their original attribution where present; see [ASSETS.md](docs/ASSETS.md).
- Seven original external paper downloads were unavailable at backup. Their original targets and recorded statuses are retained only in maintenance documentation at `content/reference-link-status.json`; original research citations remain unchanged. They were not retried or silently replaced.
- An existing malformed homepage hyperlink for the Conflict Resolution Center of Montgomery County is preserved as readable text, with no invented replacement target.

See [MIGRATION.md](docs/MIGRATION.md) and [TESTS.md](docs/TESTS.md). Running the checks locally generates `docs/verification.json` and `docs/external-links.csv`; generated reports, screenshots and local editor history are excluded from Git. The publish folder contains no account screenshots, financial/billing data, source caches, credentials, analytics or trackers.
