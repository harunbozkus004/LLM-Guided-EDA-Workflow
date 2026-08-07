# Alternative: values copied from 4-digit standard reports, period read from the clock.
read_liberty -max platform/Nangate45_slow.lib
estimate_parasitics -placement
with_output_to_variable a { report_worst_slack -max -digits 4 }
with_output_to_variable b { report_tns -digits 4 }
regexp {worst slack\s+(\S+)} $a -> wss
regexp {tns\s+(\S+)} $b -> tns
set f [open outputs/slow_corner.txt w]
puts $f "worst_setup_slack $wss"
puts $f "total_negative_setup_slack $tns"
puts $f "min_clock_period [format %.4f [expr {[get_property [get_clocks core_clock] period] - $wss}]]"
close $f
