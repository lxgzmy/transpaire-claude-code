# inclusions-upgrades fixtures

Synthetic job JSONs (invented names, lots, prices) exercising the `upgrades`
block that `edit_inclusions.py` reads - one per regional area, with the
Bathroom 2, air-conditioning, storeys and item modes (replace, replace one
line, add, insert new label, custom item) covered between them.
`regress_edit_inclusions.py` fills the live Sydney STANDARD blank with each and
checks the edited result. No real client data.
