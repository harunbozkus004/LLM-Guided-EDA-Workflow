# Alternative: re-propagate the clock, more digits, default (setup) skew report.
set_propagated_clock [all_clocks]
estimate_parasitics -placement
report_clock_skew -digits 5 > outputs/ct03_clock_skew.rpt
