# Global placement -> IO pin re-placement for the placed cells -> padded legalization.
global_placement
place_pins -hor_layers metal3 -ver_layers metal2
set_placement_padding -global -left 1 -right 1
detailed_placement
