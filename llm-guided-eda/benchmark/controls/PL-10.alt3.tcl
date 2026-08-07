# Alternative: ORFS-style -skip_io pass, pins, full global placement, padded legalization, mirroring.
global_placement -skip_io
place_pins -hor_layers metal3 -ver_layers metal2
global_placement
set_placement_padding -global -left 1 -right 1
detailed_placement
optimize_mirroring
check_placement
