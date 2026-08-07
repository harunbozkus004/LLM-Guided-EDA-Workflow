# Wrong parasitics assumption: placement-estimated RC changes the clock latencies.
estimate_parasitics -placement
report_clock_skew -setup -digits 4 > outputs/clock_skew.rpt
