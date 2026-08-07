# Alternative: capture the report in a variable and write a one-line summary.
estimate_parasitics -placement
with_output_to_variable rpt { report_clock_skew -setup -digits 6 }
set pins [regexp -all -inline {\S+/CK} $rpt]
set skew [sta::worst_clock_skew -setup]
set f [open outputs/ct03_clock_skew.rpt w]
puts $f [format "core_clock worst setup skew between %s and %s: %.4f" [lindex $pins 0] [lindex $pins 1] $skew]
close $f
