# Mistake (version pitfall): -global_route on a freshly loaded database reports no routes,
# so the file only gets the header line.
report_wire_length -net {clk clknet_*} -global_route -file outputs/clock_gr_wirelength.txt
