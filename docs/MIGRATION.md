# Migration record and decisions for review

The source project was reconstructed from the verified public backup of 30 October 2026. Neither original backup, live site, account nor domain was modified.

## Architecture

A small Python standard-library generator turns editable HTML fragments and per-post JSON into plain HTML, CSS and one pagination compatibility script. `public/` contains the selected static assets; `dist/` is the generated publish folder. There are no package dependencies, databases, form backends, analytics, account connections or copied Squarespace runtime. All page content is in the returned source. GitHub can store it without being the host.

The original desktop screenshots guided the 950px page width, 294px portrait, approximately 34px home-column gap, white background, header position, restrained colors, thin body typography, right-column press/contact layout, WorkWell banner and image/text article rows. Small-screen layouts use a native, keyboard-operable Menu disclosure and stack the editorial columns. Differences: freely licensed title font, current Source Sans family build, a rendered contact portrait that was blank in the quick archived capture, and the two omitted third-party images explained in ASSETS.md.

## Content and URLs

- Homepage biography and all homepage news paragraphs, research, teaching and press text imported without editorial rewriting.
- Contact keeps the academic profile links and clickable email address.
- Nine WorkWell posts retain their original title, full body, metadata, author and original publication milliseconds/ISO dates. A URL date can differ from the actual publication date; neither has been “corrected.”
- `/workwell-diplomacy` and `/workwelldiplomacy` are preserved as distinct landing/collection routes. Paths gain a trailing-slash static form while incoming original paths resolve through ordinary directory redirects.
- Original category/tag labels and their plus-sign URLs remain. Standard `/page/2/` and `/page/3/` work without JavaScript. Original offset query URLs are handled by a small local script; no-JavaScript visitors can use the normal page links.
- `/home` redirects to `/`; `/teaching` is an extra alias for original `/about`. Original `/s/1-June-CNMC-Hospital-Grand-Rounds-flyer-Mislin.pdf` remains a real PDF route.
- `/read-me-om` was published Squarespace template documentation, not Alexandra's personal content. Its original is preserved only in the unchanged backup; the rebuilt route redirects home. This avoids putting irrelevant template instructions and template images in the new publish folder.


## Link gaps

The seven inaccessible paper downloads are recorded only in maintenance documentation at `content/reference-link-status.json`. The former public reference-notes page and footer link were removed on 1 November 2026; original research citations remain unchanged. Four returned 404, two 403, and one failed TLS. No denied download was retried and no paper was silently substituted. External links are inventoried in `external-links.csv`; those not already known to fail were not freshly revalidated online. The old malformed Conflict Resolution Center of Montgomery County URL is plain readable text, pending a real target from the author.

## Remaining choices

1. Review the academic text and contact information.
2. Decide whether to supply permission or alternatives for the two omitted optional images.
3. Confirm the malformed original link's intended destination, if it should remain clickable.
4. Select hosting and its deployment/domain/redirect settings for this academic personal site. No hosting or billing action was taken. Railway is an available option to evaluate, not a connected service.
5. Choose the long-term editing workflow. Plain-file editing is implemented; a visual CMS, if wanted, would require separate selection and authorization.

The source is prepared for the repository `mislin11/alexandra-mislin-site`. Publication still requires the user's chosen hosting setup and authorization.
