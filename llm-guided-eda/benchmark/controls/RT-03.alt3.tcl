# Alternative: ORFS-style flow with per-layer capacity adjustments and congestion iterations.
set_global_routing_layer_adjustment metal2 0.5
set_global_routing_layer_adjustment metal3 0.5
set_global_routing_layer_adjustment metal4-metal6 0.3
set_routing_layers -clock metal4-metal6 -signal metal2-metal6
global_route -congestion_iterations 50 -allow_congestion -verbose
