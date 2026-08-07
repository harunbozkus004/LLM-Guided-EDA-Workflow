# Wrong order: parasitics estimated with the typical library, then the slow library is mapped.
estimate_parasitics -placement
read_liberty -max platform/Nangate45_slow.lib
set wns [worst_slack -max]
set f [open outputs/slow_corner.txt w]
puts $f [format "worst_setup_slack %.4f" $wns]
puts $f [format "total_negative_setup_slack %.4f" [total_negative_slack -max]]
puts $f [format "min_clock_period %.4f" [expr {0.485 - $wns}]]
close $f
