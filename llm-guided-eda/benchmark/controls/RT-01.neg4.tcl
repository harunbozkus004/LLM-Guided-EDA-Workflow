# Mistake: only the clock nets are routed (partial work), although the guides are saved.
set_nets_to_route {clk clknet_*}
global_route -guide_file outputs/gcd.guide
