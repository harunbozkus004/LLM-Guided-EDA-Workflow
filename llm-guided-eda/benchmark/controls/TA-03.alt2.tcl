# Alternative: write the skew value itself with Tcl file I/O.
set f [open outputs/clock_skew.rpt w]
puts $f [format "core_clock setup skew %.4f ns" [worst_clock_skew -setup]]
close $f
