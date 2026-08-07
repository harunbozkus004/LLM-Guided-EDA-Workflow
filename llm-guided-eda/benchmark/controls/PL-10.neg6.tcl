# Padding set but the final legalization is never run.
global_placement
place_pins -hor_layers metal3 -ver_layers metal2
set_placement_padding -global -left 1 -right 1
