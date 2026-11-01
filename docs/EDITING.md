# Your simple website editor

## Open it

Double-click **Open Website Editor.app** in the `alexandra-mislin-site` folder. Your browser opens the local editor. Keep the app inside that folder. On this Mac, no Terminal or new account is needed. If the server is already running, you can paste `http://127.0.0.1:8767/editor/` into Chrome. If the app chooses a different port, use the address it opens.

A downloaded app may receive a normal macOS first-open security prompt. Do not bypass a security warning; ask for help if macOS blocks it. The launcher executable and repeated startup were tested, but Finder's first-open dialog could not be tested because native Computer Use permission was unavailable.

## Change a page

Choose **Pages**, then the page name. Click in the text and edit normally. Select words before using **Bold**, *Italic*, headings or lists. For a link, select its words, click **Link**, enter a website address and click **Apply link**. Email links can use `mailto:mislin@american.edu`; internal page links can use `/research/`.

Click **Save & Preview**. A successful save rebuilds the local website, checks its links and refreshes the preview. **Open larger** shows a full-size view. The editor's narrower preview can show the website's mobile layout even on a desktop; the larger view shows its normal desktop layout.

Keep the page's main heading, useful image descriptions and photo credits. Pasted text keeps supported formatting and links; embedded scripts, remote images and unsupported widgets are stripped or rejected. Empty text and broken internal links cannot replace a valid saved page. If a save fails, your editing text stays in the form and the last valid website stays available.

## Add or update news

Choose **News**. Select an old entry to correct it, or click **Add news**. Enter a short **Date shown**, such as `November 2026`, then write the news text. The date is added before your text; do not type it twice. Multiple paragraphs stay together as one entry. New news goes above the older entries. Click **Save & Preview**.

## Write a blog article

Choose **Blog**, then an article or **New article**. Fill in the title, publication date, short summary and article text. You can choose an image already in the project, or use the simple text panel. New image uploads and layout changes need help; there is no image-upload service here.

New articles start with **Keep as a draft** checked. Save to see a private local preview. Drafts stay out of the public `dist/` build. Uncheck the draft box and save when you want an article included in the local website build. This still does not publish it online. The original nine published articles cannot be hidden by the editor because their old addresses and incoming links must remain valid.

Existing article addresses are kept, including when correcting a date. Ordinary text edits preserve the exact original publication timestamp. A deliberate date correction uses midnight UTC on the selected day. New articles receive a stable address from their first saved title and date; later title edits do not change it. Original tags/categories are retained; the editor does not offer category management.

## Replace your CV

Choose **CV**, select your new PDF (up to 8 MB), then **Save CV & Preview**. Confirm the replacement. The old PDF is kept in History and the CV link keeps its existing address. The preview opens the locally saved PDF.

## Cancel, undo and recover

- **Cancel changes** asks before discarding unsaved text. **Keep editing** returns to your form.
- **Undo typing** and **Redo typing** act within the text field; **Undo last save** restores the content from before the most recent successful save.
- **History** lists previous saves. **Restore version before this save** restores only the item(s) changed by that save. The version you replace is also kept, so a restore can itself be undone.
- If a tab reloads, select the same item (or **New article** / **Add news**) and use **Recover unsaved edit**. Browser recovery is a convenience, not a backup; it depends on that browser's local storage.
- Saves use conflict checks: two tabs cannot silently overwrite each other's newer content. If told to reload, your unsaved text remains recoverable for review.

Saved content lives in the source files on this Mac. History lives in the private `.local-editor/` folder and is not included in the portable source ZIP, Git repository or website output. Keep a separate backup of the entire working folder if you want to preserve that private history. The interface shows the most recent 100 successful saves; older records remain on disk. Do not edit private history files manually.

## What Save means

**Save & Preview changes only your local working copy.** Your live Squarespace website stays unchanged. Nothing is uploaded to GitHub, Railway or a host. A future publish workflow must be selected and approved separately. Only `dist/` is public static output; never serve the project root or the private editor on a public host.

The editor is restricted to this Mac's loopback interface. It deliberately has no remote login. The mobile layout was checked at 390 pixels for responsive usability; it does not make the service reachable from your phone.

## For a future maintainer

The architecture remains portable: editable HTML fragments and JSON metadata feed the dependency-free Python builder. The editor manages those files through validated forms, staged builds, optimistic revisions and recoverable transactions. Build with `python3 tools/build.py`, check with `python3 tools/check.py`, and test the editor in a temporary copy with `python3 tools/test_editor.py`.

`--strict-migration` compares against the original import and is expected to report intentional updates after editing. The normal check validates the current content and publication metadata. The optional container copies only `dist/` and the view-only static server into its final image. Its public server has no editing endpoints.
