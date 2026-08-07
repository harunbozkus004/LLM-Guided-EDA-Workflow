# Deletes the clock first: the IO delays referencing core_clock are removed with it.
delete_clock [get_clocks core_clock]
create_clock -name core_clock -period 0.40 [get_ports clk]
set f [open outputs/period_0p40.txt w]
puts $f [format "worst_setup_slack %.4f" [worst_slack -max]]
puts $f "setup_violating_endpoints [sta::endpoint_violation_count max]"
close $f
