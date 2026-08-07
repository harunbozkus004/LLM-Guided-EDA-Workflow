# Alternative: explicit clock object, report captured in a variable and written with puts.
estimate_parasitics -placement
set rpt [with_output_to_variable v { report_clock_skew -setup -clock [get_clocks core_clock] -digits 4 }]
set f [open outputs/ct03_clock_skew.rpt w]
puts -nonewline $f $v
close $f
