# Source coverage review — September 25, 2026

## What was checked

All 52 active-scope public/operational archive pages were requested. The separate discovery run attempted the 34 configured automated sources and 10 ready-for-testing candidates. Five production manual sources, two manual-setup candidates and one adapter-needed candidate were retained as explicit work items.

Archive reachability: 41 HTTP 200, five HTTP 202 verification responses, four HTTP 403 responses, one HTTP 404, and one timeout. These are observations from this environment, not permanent availability claims. A successful page fetch does not establish document completeness, correct body attribution, or PDF extraction.

The discovery run found candidate documents for Coopersville, Hudsonville, Otsego city, Saugatuck city and Zeeland city. It skipped PDF enrichment and did not activate them. Subsequent targeted PDF checks are recorded below.

## Remaining work

- Resolve access verification/blocks for Fillmore, Laketown, Crockery, Polkton, Ferrysburg, Park, Spring Lake Township and Zeeland Township. Do not bypass site challenges.
- Replace or verify the missing Olive Township document-category page; its RSS feed is a separate endpoint.
- Verify the Village of Spring Lake independently; do not substitute Spring Lake Township. The earlier compatibility review flagged a municipality identity collision.
- Manlius exposed an old Planning Commission document; verify a current archive. Salem has parseable dates but may have no documents inside the collection window.
- Clyde and Hopkins village need a supported collection setup; Wayland city needs an adapter.
- Review document/body/date correctness and PDF results for each trial source before promotion.
- PDF packets over 10 MiB remain linked with a reported extraction failure. Scanned PDFs need OCR.
- A source can return zero matches because its archive is stale or its document pattern is not supported. The app labels this as no matching documents, never as proof that no meeting occurred.

## Archive reachability

| Source ID | Municipality / body | Deployment | Archive response |
| --- | --- | --- | --- |
| ALG-ALLE-TWP-PC | Allegan Township Planning Commission | Production | 200 |
| ALG-CASC-TWP-PC | Casco Township Planning Commission | Production | 200 |
| ALG-CHES-TWP-PC | Cheshire Township Planning Commission | Production | 200 |
| ALG-CLYD-TWP-PC | Clyde Township Planning Commission | Manual Setup Needed | 200 |
| ALG-DORR-TWP-PC | Dorr Township Planning Commission | Production | 200 |
| ALG-FILL-TWP-PC | Fillmore Township Planning Commission | Production | 202 — verification page |
| ALG-GANG-TWP-PC | Ganges Township Planning Commission | Production | 200 |
| ALG-GUNP-TWP-PC | Gun Plain Township Planning Commission | Production | 200 |
| ALG-HEAT-TWP-PC | Heath Township Planning Commission | Production | 200 |
| ALG-HOPK-TWP-PC | Hopkins Township Planning Commission | Production | Timeout / request error |
| ALG-LAKE-TWP-PC | Laketown Township Planning Commission | Production | 202 — verification page |
| ALG-LEE-TWP-PC | Lee Township Planning Commission | Production | 200 |
| ALG-LEIG-TWP-PC | Leighton Township Planning Commission | Production | 200 |
| ALG-MANL-TWP-PC | Manlius Township Planning Commission | Ready for Testing | 200 |
| ALG-MART-TWP-PC | Martin Township Planning Commission | Production | 200 |
| ALG-MONT-TWP-PC | Monterey Township Planning Commission | Production | 200 |
| ALG-OTSE-TWP-PC | Otsego Township Planning Commission | Production | 200 |
| ALG-OVER-TWP-PC | Overisel Township Planning Commission | Production | 200 |
| ALG-SALE-TWP-PC | Salem Township Planning Commission | Ready for Testing | 200 |
| ALG-SAUG-TWP-PC | Saugatuck Township Planning Commission | Production | 200 |
| ALG-TROW-TWP-PC | Trowbridge Township Planning Commission | Production | 200 |
| ALG-VALL-TWP-PC | Valley Township Planning Commission | Production | 200 |
| ALG-WATS-TWP-PC | Watson Township Planning Commission | Production | 200 |
| ALG-WAYL-TWP-PC | Wayland Township Planning Commission | Production | 200 |
| ALG-ALLE-CITY-PC | City of Allegan Planning Commission | Production | 200 |
| OTT-ALLE-TWP-PC | Allendale Charter Township Planning Commission | Production | 200 |
| OTT-BLEN-TWP-PC | Blendon Township Planning Commission | Production | 200 |
| OTT-CHES-TWP-PC | Chester Township Planning Commission | Production | 200 |
| OTT-CROC-TWP-PC | Crockery Township Planning Commission | Production | 202 — verification page |
| OTT-GEOR-TWP-PC | Georgetown Charter Township Planning Commission | Production | 200 |
| OTT-GRHV-TWP-PC | Grand Haven Charter Township Planning Commission | Production | 200 |
| OTT-HOLL-TWP-PC | Holland Charter Township Planning Commission | Production | 200 |
| OTT-JAME-TWP-PC | Jamestown Charter Township Planning Commission | Production | 200 |
| OTT-OLIV-TWP-PC | Olive Township Planning Commission | Production | 404 |
| OTT-PARK-TWP-PC | Park Township Planning Commission | Production | 403 |
| OTT-POLK-TWP-PC | Polkton Charter Township Planning Commission | Production | 202 — verification page |
| OTT-PORT-TWP-PC | Port Sheldon Township Planning Commission | Production | 200 |
| OTT-ROBI-TWP-PC | Robinson Township Planning Commission | Production | 200 |
| OTT-SPRL-TWP-PC | Spring Lake Township Planning Commission | Production | 403 |
| OTT-TALL-TWP-PC | Tallmadge Charter Township Planning Commission | Production | 200 |
| OTT-WRIG-TWP-PC | Wright Township Planning Commission | Production | 200 |
| OTT-ZEEC-TWP-PC | Zeeland Charter Township Planning Commission | Production | 403 |
| OTT-COOP-CITY-PC | City of Coopersville Planning Commission | Production (proposed) | 200 |
| OTT-FERR-CITY-PC | City of Ferrysburg Planning Commission | Ready for Testing | 202 — verification page |
| OTT-GRHV-CITY-PC | City of Grand Haven Planning Commission | Ready for Testing | 200 |
| OTT-HUDS-CITY-PC | City of Hudsonville Planning Commission | Production (proposed) | 200 |
| ALG-OTSE-CITY-PC | City of Otsego Planning Commission | Ready for Testing | 200 |
| ALG-SAUG-CITY-PC | City of Saugatuck Planning Commission | Ready for Testing | 200 |
| ALG-WAYL-CITY-PC | City of Wayland Planning Commission | Adapter Needed | 200 |
| OTT-ZEEL-CITY-PC | City of Zeeland Planning Commission | Ready for Testing | 200 |
| ALG-HOPK-VILL-PC | Village of Hopkins Planning Commission | Manual Setup Needed | 200 |
| OTT-SPRL-VILL-PC | Village of Spring Lake Planning Commission | Ready for Testing | 403 |

## Verification limits

The workbook/registry parity, original 39 operational endpoints and stable IDs, date parsing, mixed-board scoping, relative URLs, one-level document traversal, oversize PDFs, invalid feed preservation and refresh replacement have offline regression coverage. The application passes lint and production build.

A browser visual check could not run: the runtime lacked a Chromium executable and its download returned an invalid archive. No browser screenshot or successful end-to-end UI result is claimed. Azure deployment remains untested until the change is reviewed and deployed with the repository secret.

The original published `public/feed.json` is unchanged by the isolated audits. Coopersville and Hudsonville are enabled in the proposed workbook/configuration. No production deployment was performed for this review.

## Targeted PDF verification

| Source | Documents | Outcome | Configuration decision |
| --- | ---: | --- | --- |
| City of Coopersville | 4 | All four PDFs fetched and parsed. Municipality, Planning Commission body and meeting dates checked in extracted document headers. | Enable in this change. |
| City of Hudsonville | 4 | All four PDFs fetched and parsed. Municipality, Planning Commission body and meeting dates checked in extracted document headers. | Enable in this change. |
| City of Saugatuck | 5 | Two packets exceeded 10 MiB; archive also has conflicting historical labels. Links are retained, extraction gaps reported. | Keep pending. |
| City of Zeeland | 4 | One cancellation PDF had no extractable text in the first six pages. | Keep pending. |

This brings the proposed configuration to 36 automated sources, five manual
production entries and 11 pending entries. All 52 remain visible in Sources.
23 offline regression tests pass. The two workbook promotions preserve every
other original cell value, both validation rules, all four sheet names and
freeze panes. Added endpoint rows were visually checked.

## Publication scope

The draft preserves the existing scheduled scraping workflow unchanged. Automatic
approval review blocked the proposed scheduled deployment changes because the
publication approval did not separately authorize automatic Azure deployments.
Daily source-status publication and automated deployment are therefore still
unfinished; source statuses remain unavailable on the live site until those
generated files are included in an authorized release.
