# Alternative: map the slow library onto the default corner for all delays (setup values are
# identical), and take the minimum period from the STA min-period search including IO paths.
read_liberty -corner default platform/Nangate45_slow.lib
estimate_parasitics -placement
set clk [get_clocks core_clock]
set minp [sta::time_sta_ui [sta::find_clk_min_period $clk 1]]
set f [open outputs/slow_corner.txt w]
puts $f "worst_setup_slack [format %.4f [worst_slack -max]]"
puts $f "total_negative_setup_slack [format %.4f [total_negative_slack -max]]"
puts $f "min_clock_period [format %.4f $minp]"
close $f
