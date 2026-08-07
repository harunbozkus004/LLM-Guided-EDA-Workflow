# Alternative: command units switched to pF, so the 10 fF limit is given as 0.010.
set_cmd_units -time ns -capacitance pF
estimate_parasitics -placement
set_max_transition 0.05 [current_design]
set_max_capacitance 0.010 [current_design]
report_check_types -max_slew -violators > outputs/max_transition_violations.rpt
report_check_types -max_capacitance -violators > outputs/max_capacitance_violations.rpt
