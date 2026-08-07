# Setup clock skew of core_clock (propagated clock, no wire parasitics).
report_clock_skew -setup -clock core_clock -digits 4 > outputs/clock_skew.rpt
