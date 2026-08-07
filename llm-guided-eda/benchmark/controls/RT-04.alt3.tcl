# Alternative: the stored routes are loaded explicitly; value written with a label and unit.
grt::have_routes
estimate_parasitics -global_routing
set fh [open outputs/wns_grt.txt w]
puts $fh "WNS: [format %.4f [sta::worst_slack -max]] ns"
close $fh
