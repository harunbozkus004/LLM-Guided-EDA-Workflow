# Alternative: deterministic random seed, critical-net handling and the guides also saved.
set_routing_layers -signal metal2-metal6 -clock metal4-metal6
set_global_routing_random -seed 7
global_route -critical_nets_percentage 30 -guide_file outputs/rt03.guide
