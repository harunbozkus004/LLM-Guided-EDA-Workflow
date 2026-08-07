# Parasitics from the stored global routing, then the worst setup slack.
estimate_parasitics -global_routing
set fh [open outputs/wns_grt.txt w]
puts $fh [format %.4f [sta::worst_slack -max]]
close $fh
