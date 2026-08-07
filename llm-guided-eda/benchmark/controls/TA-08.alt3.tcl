# Alternative: a plain read of the slow library (remaps the cells for min and max delays),
# then the placement RC estimate, which also refreshes the timing graph.
read_liberty platform/Nangate45_slow.lib
estimate_parasitics -placement
set wns [worst_slack -max]
set f [open outputs/slow_corner.txt w]
puts $f [format "worst_setup_slack %.4f" $wns]
puts $f [format "total_negative_setup_slack %.4f" [total_negative_slack -max]]
puts $f [format "min_clock_period %.4f" [expr {0.485 - $wns}]]
close $f
