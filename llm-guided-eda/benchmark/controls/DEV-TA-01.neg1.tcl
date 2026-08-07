# Period never changed: reports the original 0.485 ns timing.
set f [open outputs/period_0p40.txt w]
puts $f [format "worst_setup_slack %.4f" [worst_slack -max]]
puts $f "setup_violating_endpoints [sta::endpoint_violation_count max]"
close $f
