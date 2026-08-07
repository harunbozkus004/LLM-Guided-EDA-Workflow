# Alternative: ORFS detail_place recipe after the padded legalization (improve_placement keeps the padding).
global_placement
place_pins -hor_layers metal3 -ver_layers metal2
set_placement_padding -global -left 1 -right 1
detailed_placement
improve_placement
optimize_mirroring
