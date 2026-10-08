# inclusions-upgrades fixtures

Synthetic job JSONs (invented names, lots, prices) exercising the `upgrades`
block that `edit_inclusions.py` reads - one per regional area, with the
Bathroom 2, air-conditioning, storeys and item modes (replace, replace one
line, add, insert new label, custom item) covered between them.
`regress_edit_inclusions.py` fills the live Sydney STANDARD blank with each and
checks the edited result. No real client data.

Since 8 Oct 2026 (CD-9.11): a fixture with `"_blank": "auxiliary"` runs on the
Sydney AUXILIARY blank (split MAIN / AUX DWELLING upgrades) - `aux-main-and-aux`
(items in both dwellings, `mode: remove`, `before`), `aux-no-dwelling` (no
`dwelling` key: MAIN, flagged). A fixture with `"_expect_error"` must make the
editor refuse with that message and write nothing - `standard-aux-item-refused`
(an `aux` item on the STANDARD blank).
