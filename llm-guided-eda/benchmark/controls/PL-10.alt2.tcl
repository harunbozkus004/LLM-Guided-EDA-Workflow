# Alternative: re-run global placement after the pins moved, then legalize with padding.
global_placement -density 0.6
place_pins -hor_layers metal3 -ver_layers metal2 -corner_avoidance 2
global_placement -density 0.6
set_placement_padding -global -right 1 -left 1
detailed_placement
