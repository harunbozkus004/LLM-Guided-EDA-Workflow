# Copies the floorplan recipe: random pin placement is not wirelength-driven (same seed, same pins).
global_placement
place_pins -random -hor_layers metal3 -ver_layers metal2
set_placement_padding -global -left 1 -right 1
detailed_placement
