# Alternative: separate layer-range calls plus harmless extras (resource reduction, verbose, guide file).
set_routing_layers -signal metal2-metal6
set_routing_layers -clock metal4-metal6
set_global_routing_layer_adjustment metal2-metal6 0.5
global_route -verbose -guide_file outputs/gcd.guide
