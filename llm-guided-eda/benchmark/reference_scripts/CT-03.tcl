# Post-CTS clock skew (setup) with placement-based parasitics.
estimate_parasitics -placement
report_clock_skew -setup -clock core_clock -digits 4 > outputs/ct03_clock_skew.rpt
