# Alternative: one free-text line that also contains an integer (the digit count).
set f [open outputs/clock_skew.rpt w]
puts $f "Setup clock skew of core_clock: [format %.4f [worst_clock_skew -setup]] ns (4 decimal places)"
close $f
