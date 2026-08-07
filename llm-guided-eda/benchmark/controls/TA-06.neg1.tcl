# Unit mistake: capacitance limit given as 0.01 (pF) although command units are fF.
estimate_parasitics -placement
set_max_transition 0.05 [current_design]
set_max_capacitance 0.01 [current_design]
report_check_types -max_slew -violators > outputs/max_transition_violations.rpt
report_check_types -max_capacitance -violators > outputs/max_capacitance_violations.rpt
