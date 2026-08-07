# Wrong vertical pin layer (metal4 instead of metal2) on the top/bottom edges.
global_placement
place_pins -hor_layers metal3 -ver_layers metal4
set_placement_padding -global -left 1 -right 1
detailed_placement
