# Missing prerequisite: without placement parasitics the repair works on wire-load timing
# and sees only 4 violating endpoints.
repair_timing -setup -repair_tns 100
detailed_placement
