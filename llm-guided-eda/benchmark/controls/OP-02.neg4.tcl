# Wrong check type: a setup margin instead of a hold margin.
estimate_parasitics -placement
repair_timing -setup -setup_margin 0.08
detailed_placement
