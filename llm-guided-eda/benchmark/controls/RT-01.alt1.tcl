# Alternative: platform layer settings, route first, then dump the stored guides separately.
set_global_routing_layer_adjustment metal2-metal10 0.5
set_routing_layers -signal metal2-metal10 -clock metal6-metal10
global_route -verbose -congestion_iterations 100
write_guides outputs/gcd.guide
