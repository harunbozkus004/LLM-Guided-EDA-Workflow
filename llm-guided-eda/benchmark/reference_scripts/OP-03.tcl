# Setup repair on all violating endpoints (this build repairs only the worst endpoint
# unless -repair_tns is given), then re-legalize.
estimate_parasitics -placement
repair_timing -setup -repair_tns 100
detailed_placement
