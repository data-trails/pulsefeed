# PulseFeed

Planning Commission updates for Allegan and Ottawa counties. A Python collector
writes a static JSON feed; the React/Vite app displays it on Azure Static Web Apps.

## Source management

Edit **`config/pulsefeed_master_sources.xlsx`**. This is the one governed inventory.
`config/sources.json` is generated and consumed by both Python and the app. Do not
maintain a second list in JavaScript or Python.

The imported workbook contains 52 active-scope sources: 41 production entries
(36 automated, five manual), and 11 pending entries. Coopersville and Hudsonville
were enabled after live archive/PDF checks; the original 39 endpoints are preserved. Its 28 `Hold - Future Scope`
rows are retained in the workbook but excluded from the app and collection.
Production means configured, not verified healthy.

After saving and closing Excel:

```bash
python scraper/source_workbook.py --write
python scraper/source_workbook.py --check
```

Commit the workbook and generated JSON together. The collector validates their
agreement before running; regenerate the JSON locally after workbook edits. Formula cells, duplicate identities, missing
production endpoints, unsupported handlers and inconsistent RSS URLs fail before
collection. Paths resolve from the repository regardless of the working directory.

- **Active Sources:** source identity, public link, deployment status and legacy name.
- **Source Endpoints:** exact operational URLs and handler assignments. These can
  differ from the public link. Preserve legacy names to retain saved-item IDs.
- **Deployment Status:** only `Production` activates a collector. `Ready for Testing`
  supports isolated trials. `Manual Setup Needed`, `Adapter Needed`, and
  `Source Verification Needed` remain explicit work items.
- **Hold - Future Scope:** research inventory only; never activated implicitly.

Current handlers: RSS plus HTML, manual review, Joomla document downloads, and
CivicPlus AgendaCenter. The HTML collector also handles dated PDF links,
`?ddownload=` links, HTML base URLs, and one level of `/document/` landing pages.
It requires Planning Commission context and rejects conflicting document dates.
Adding an unsupported platform still requires an adapter and tests.

## Run locally

Python 3.12 and Node 22 or later are recommended for this repository.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r scraper/requirements.txt
npm ci
python scraper/source_workbook.py --check
python scraper/scrape.py
npm run dev
```

Collection writes `public/feed.json` and `public/source-status.json`. Individual
source failures are reported and do not stop other sources. Existing in-window
items are retained when a source fails; refreshed records replace the same stable
ID. Invalid existing JSON stops the run instead of silently erasing history.
The existing window is retained: the later of January 1 and 91 days ago, up to
365 days ahead. There is no global 300-record cap hiding quieter sources.

PDF downloads are limited to 10 MiB and extraction to the first six pages. Larger
or unreadable documents remain linked, with the extraction problem in source
status. Scanned/image-only PDFs need OCR, which is not implemented. Source status
is collection evidence, not a completeness guarantee. Publication dates from RSS
are labeled internally and excluded from the meeting calendar.

The current repository does not implement email ingestion. The earlier standalone
README describing email and workbook support did not match the main branch.
This change implements workbook support; it does not configure an inbox.

## Test sources without touching the published feed

```bash
python scraper/scrape.py --source OTT-COOP-CITY-PC --include-candidates --output-dir /tmp/pulsefeed-trial
python scraper/scrape.py --include-candidates --discovery-only --output-dir /tmp/pulsefeed-audit
```

Trial records are written to `candidate-feed.json`, separate from production
records. Trial runs do not change deployment status. `--discovery-only` skips PDF
extraction and therefore cannot establish successful PDF parsing. Partial and
trial runs require an output directory outside `public/`.

Review municipality, meeting body, date, document link, PDF extraction and current
coverage before adding production endpoints and promoting a candidate. A 200
response, or zero matches, does not prove complete coverage. HTTP 202 verification
pages, access blocks, timeouts and PDF errors are reported explicitly.

## Checks and deployment

```bash
python -m unittest discover -s scraper -p 'test_*.py' -q
npm run lint
npm run build
```

Pull requests run configuration checks, Python regression tests, lint and build.
The original 39-source fixture protects names, operational endpoints and ID parity;
update it deliberately when approving a production expansion.

The existing scheduled workflow is unchanged in this draft. It collects and
commits `public/feed.json`; it does not commit `public/source-status.json` or
deploy the refreshed data. Publishing source results and adding automatic daily
Azure deployment remain unfinished. Changes to scheduled publishing were blocked
by automatic approval review and need separate authorization.

For a reviewed manual release, run the collector, include both generated public
JSON files in the release, and deploy Vite's `dist/` output. The Azure push/PR
workflow now points to `dist/`. Commits made with `GITHUB_TOKEN` do not trigger
another push workflow, so daily collection alone does not ensure a website refresh.

The Sources tab shows all in-scope sources and their latest collection outcome.
An unavailable feed shows an error; it never substitutes fictional sample updates.
Refresh fetches the published files; it does not run the Python scraper in the browser.
