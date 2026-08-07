# Alternative: load the global routes via the parasitics estimator, select the clock nets by
# name pattern and reformat the router's per-net report.
estimate_parasitics -global_routing
report_wire_length -net {clk clknet_*} -global_route -file outputs/clk_wl.csv
set in [open outputs/clk_wl.csv r]
set out [open outputs/clock_gr_wirelength.txt w]
while {[gets $in line] >= 0} {
  if {[regexp {^grt:\s+(\S+)\s+(\S+)} $line -> net wl]} { puts $out "$net $wl" }
}
close $in
close $out
