# Alternative: global padding, legalization with a displacement limit, mirroring and a verbose check.
set_placement_padding -global -left 2 -right 2
detailed_placement -max_displacement {500 100}
optimize_mirroring
check_placement -verbose
