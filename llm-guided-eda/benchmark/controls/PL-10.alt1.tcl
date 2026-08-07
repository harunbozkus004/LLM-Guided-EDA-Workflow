# Alternative: platform flow recipe for global placement, then pins, padded legalization and a check.
set_global_routing_layer_adjustment metal2-metal10 0.5
set_routing_layers -signal metal2-metal10 -clock metal6-metal10
global_placement -routability_driven -density 0.3 -pad_left 2 -pad_right 2
place_pins -hor_layers metal3 -ver_layers metal2
set_placement_padding -global -left 1 -right 1
detailed_placement
check_placement -verbose
