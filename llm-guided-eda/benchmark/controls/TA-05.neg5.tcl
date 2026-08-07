# Layout mistake: WNS and TNS on two lines instead of one.
estimate_parasitics -global_routing
set f [open outputs/wns_tns.txt w]
puts $f [format "WNS=%.4f" [worst_slack -max]]
puts $f [format "TNS=%.4f" [total_negative_slack -max]]
close $f
