# Alternative: limits before RC estimation, reports captured and written with Tcl file I/O.
set_max_capacitance 10 [current_design]
set_max_transition 0.05 [current_design]
estimate_parasitics -placement
with_output_to_variable r1 { report_check_types -max_slew -violators -digits 4 }
with_output_to_variable r2 { report_check_types -max_capacitance -violators -digits 4 }
set f [open outputs/max_transition_violations.rpt w]; puts $f $r1; close $f
set f [open outputs/max_capacitance_violations.rpt w]; puts $f $r2; close $f
