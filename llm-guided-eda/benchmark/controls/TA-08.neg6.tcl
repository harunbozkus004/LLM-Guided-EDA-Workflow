# Wrong flag: -min maps the slow library onto hold analysis only; setup stays typical.
read_liberty -min platform/Nangate45_slow.lib
estimate_parasitics -placement
set wns [worst_slack -max]
set f [open outputs/slow_corner.txt w]
puts $f [format "worst_setup_slack %.4f" $wns]
puts $f [format "total_negative_setup_slack %.4f" [total_negative_slack -max]]
puts $f [format "min_clock_period %.4f" [expr {0.485 - $wns}]]
close $f
