# Slow-corner setup check: -max maps the slow-library cells onto max-delay (setup) analysis.
read_liberty -max platform/Nangate45_slow.lib
# Estimate the RC after the library switch so the reduced parasitics use slow-corner pin data.
estimate_parasitics -placement
set wns [worst_slack -max]
set tns [total_negative_slack -max]
# All checks are single-cycle on core_clock with absolute IO delays: slack shifts 1:1 with the period.
set period [get_property [get_clocks core_clock] period]
set f [open outputs/slow_corner.txt w]
puts $f [format "worst_setup_slack %.4f" $wns]
puts $f [format "total_negative_setup_slack %.4f" $tns]
puts $f [format "min_clock_period %.4f" [expr {$period - $wns}]]
close $f
