# Alternative: verbose violation reports.
estimate_parasitics -placement
set_max_transition 0.05 [current_design]
set_max_capacitance 10 [current_design]
report_check_types -max_slew -violators -verbose > outputs/max_transition_violations.rpt
report_check_types -max_capacitance -violators -verbose > outputs/max_capacitance_violations.rpt
