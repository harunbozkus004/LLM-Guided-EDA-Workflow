# RC from the global routes already stored in the database (no re-routing).
estimate_parasitics -global_routing
set f [open outputs/wns_tns.txt w]
puts $f [format "WNS=%.4f TNS=%.4f" [worst_slack -max] [total_negative_slack -max]]
close $f
