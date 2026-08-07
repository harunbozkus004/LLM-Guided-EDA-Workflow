# Alternative: redefine the clock and explicitly re-apply the unchanged IO delays,
# count violating endpoints with the path API.
create_clock -name core_clock -period 0.40 [get_ports clk]
set_input_delay 0.097 -clock core_clock [lsearch -inline -all -not -exact [all_inputs] [get_ports clk]]
set_output_delay 0.097 -clock core_clock [all_outputs]
set n 0
foreach pe [find_timing_paths -path_delay max -group_count 100000 -endpoint_count 1] {
  if {[$pe slack] < 0} { incr n }
}
set f [open outputs/period_0p40.txt w]
puts $f "worst_setup_slack [format %.4f [worst_slack -max]]"
puts $f "setup_violating_endpoints $n"
close $f
