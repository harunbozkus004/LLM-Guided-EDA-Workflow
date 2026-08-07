# Mistake: global routing is re-run (default settings) before reporting.
global_route
report_wire_length -net {clk clknet_*} -global_route -file outputs/clock_gr_wirelength.txt
