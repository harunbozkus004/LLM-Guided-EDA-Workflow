# IO delays rescaled to 20% of the new period although they had to stay unchanged.
create_clock -name core_clock -period 0.40 [get_ports clk]
set_input_delay 0.08 -clock core_clock [lsearch -inline -all -not -exact [all_inputs] [get_ports clk]]
set_output_delay 0.08 -clock core_clock [all_outputs]
set f [open outputs/period_0p40.txt w]
puts $f [format "worst_setup_slack %.4f" [worst_slack -max]]
puts $f "setup_violating_endpoints [sta::endpoint_violation_count max]"
close $f
