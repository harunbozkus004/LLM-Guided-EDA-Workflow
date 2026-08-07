# Alternative: flow-style legalization with one site of padding, then an explicit legality check.
set_placement_padding -global -left 1 -right 1
detailed_placement
check_placement -verbose
