# Alternative: the platform flow recipe (routability-driven, density 0.3, padding during global placement).
set_global_routing_layer_adjustment metal2-metal10 0.5
set_routing_layers -signal metal2-metal10 -clock metal6-metal10
global_placement -routability_driven -density 0.3 -pad_left 2 -pad_right 2
