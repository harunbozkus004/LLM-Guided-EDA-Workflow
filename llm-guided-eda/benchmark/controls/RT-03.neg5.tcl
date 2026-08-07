# Mistake: only the clock nets are routed with the requested layers.
set_routing_layers -signal metal2-metal6 -clock metal4-metal6
set_nets_to_route {clk clknet_*}
global_route
