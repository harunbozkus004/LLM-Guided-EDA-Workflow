# Alternative: typical-corner timing is queried first; estimating after the library switch
# refreshes the timing, so the slow-corner values are correct.
puts "typical WNS (no RC): [worst_slack -max]"
read_liberty -max platform/Nangate45_slow.lib
estimate_parasitics -placement
set wns [worst_slack -max]
set f [open outputs/slow_corner.txt w]
puts $f [format "worst_setup_slack %.4f" $wns]
puts $f [format "total_negative_setup_slack %.4f" [total_negative_slack -max]]
puts $f [format "min_clock_period %.4f" [expr {0.485 - $wns}]]
close $f
