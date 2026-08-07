# Alternative: query the violators through the STA API and list one pin name per line.
set_max_transition 0.05 [current_design]
set_max_capacitance 10 [current_design]
estimate_parasitics -placement
set f [open outputs/max_transition_violations.rpt w]
foreach pin [sta::check_slew_limits NULL 1 NULL max] { puts $f [get_full_name $pin] }
close $f
set f [open outputs/max_capacitance_violations.rpt w]
foreach pin [sta::check_capacitance_limits NULL 1 NULL max] { puts $f [get_full_name $pin] }
close $f
