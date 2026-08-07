# Alternative: extra exploratory timing reports before estimating parasitics.
report_checks -path_delay max
report_clock_skew -setup
estimate_parasitics -placement
report_clock_skew -setup -clock core_clock -digits 4 > outputs/ct03_clock_skew.rpt
