# Alternative: skew report surrounded by unrelated clock-property tables.
report_clock_properties core_clock > outputs/clock_skew.rpt
report_clock_skew -setup -clock core_clock -digits 4 >> outputs/clock_skew.rpt
report_clock_properties core_clock >> outputs/clock_skew.rpt
