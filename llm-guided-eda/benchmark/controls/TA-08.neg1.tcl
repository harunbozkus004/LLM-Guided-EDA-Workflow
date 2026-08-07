# Precision mistake: minimum period copied from the 2-decimal minimum-period report.
read_liberty -max platform/Nangate45_slow.lib
estimate_parasitics -placement
with_output_to_variable rpt { report_clock_min_period -include_port_paths }
regexp {period_min = (\S+)} $rpt -> minp
set f [open outputs/slow_corner.txt w]
puts $f [format "worst_setup_slack %.4f" [worst_slack -max]]
puts $f [format "total_negative_setup_slack %.4f" [total_negative_slack -max]]
puts $f "min_clock_period $minp"
close $f
