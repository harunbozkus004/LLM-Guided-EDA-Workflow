# Wrong report kind: worst setup path instead of the clock-skew report.
estimate_parasitics -placement
report_checks -path_delay max -format full_clock_expanded -digits 4 > outputs/ct03_clock_skew.rpt
