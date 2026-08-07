# Mistake: guides saved, then the design is re-routed with other layers, so the file is stale.
global_route -guide_file outputs/gcd.guide
set_routing_layers -signal metal2-metal6 -clock metal4-metal6
global_route
