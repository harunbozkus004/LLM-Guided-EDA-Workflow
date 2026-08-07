# Alternative: find the minimum period empirically by bisection on a redefined clock,
# after recording the slow-corner values at the original period.
read_liberty -max platform/Nangate45_slow.lib
estimate_parasitics -placement
set wns [worst_slack -max]
set tns [total_negative_slack -max]
set lo 0.485
set hi 4.0
while {$hi - $lo > 1e-6} {
  set mid [expr {($lo + $hi) / 2.0}]
  create_clock -name core_clock -period $mid [get_ports clk]
  if {[worst_slack -max] >= 0} { set hi $mid } else { set lo $mid }
}
create_clock -name core_clock -period 0.485 [get_ports clk]
set f [open outputs/slow_corner.txt w]
puts $f [format "worst_setup_slack %.4f" $wns]
puts $f [format "total_negative_setup_slack %.4f" $tns]
puts $f [format "min_clock_period %.4f" $hi]
close $f
