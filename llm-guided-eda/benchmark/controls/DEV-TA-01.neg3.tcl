# Wrong clock name: a new clock on clk replaces core_clock and drops the IO delays on it.
create_clock -name clk_0p40 -period 0.40 [get_ports clk]
set f [open outputs/period_0p40.txt w]
puts $f [format "worst_setup_slack %.4f" [worst_slack -max]]
puts $f "setup_violating_endpoints [sta::endpoint_violation_count max]"
close $f
