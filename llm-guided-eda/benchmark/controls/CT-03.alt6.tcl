# Alternative: the clock is (re-)propagated after the parasitics were estimated.
estimate_parasitics -placement
set_propagated_clock [all_clocks]
report_clock_skew -setup -clock core_clock -digits 4 > outputs/ct03_clock_skew.rpt
