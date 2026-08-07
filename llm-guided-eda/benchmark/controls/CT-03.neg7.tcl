# Modifies the design: post-CTS timing repair before reporting (resizes cells).
repair_timing
estimate_parasitics -placement
report_clock_skew -setup -clock core_clock -digits 4 > outputs/ct03_clock_skew.rpt
