# Missing step: the limits are never applied (only the library limits are checked).
estimate_parasitics -placement
report_check_types -max_slew -violators > outputs/max_transition_violations.rpt
report_check_types -max_capacitance -violators > outputs/max_capacitance_violations.rpt
