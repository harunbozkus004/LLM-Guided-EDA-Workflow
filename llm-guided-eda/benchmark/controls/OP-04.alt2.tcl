# Alternative: two repair passes, rules applied per object type, colon-separated report.
set_max_transition 0.05 [current_design]
set_max_capacitance 10 [current_design]
set_max_fanout 10 [current_design]
estimate_parasitics -placement
set b_slew [llength [sta::check_slew_limits NULL 1 NULL max]]
set b_cap [llength [sta::check_capacitance_limits NULL 1 NULL max]]
set b_fo [llength [sta::check_fanout_limits NULL 1 max]]
report_check_types -max_slew -max_capacitance -max_fanout -violators
repair_design
repair_design
detailed_placement
check_placement
estimate_parasitics -placement
report_check_types -max_slew -max_capacitance -max_fanout -violators
set fh [open outputs/drv_summary.txt w]
puts $fh "max_slew: $b_slew [llength [sta::check_slew_limits NULL 1 NULL max]]"
puts $fh "max_capacitance: $b_cap [llength [sta::check_capacitance_limits NULL 1 NULL max]]"
puts $fh "max_fanout: $b_fo [llength [sta::check_fanout_limits NULL 1 max]]"
close $fh
