# Alternative: the router's own per-net report (header + "grt: <net> <wl> <pins>") written as is.
estimate_parasitics -global_routing
report_wire_length -net {clk clknet_*} -global_route -file outputs/clock_gr_wirelength.txt
