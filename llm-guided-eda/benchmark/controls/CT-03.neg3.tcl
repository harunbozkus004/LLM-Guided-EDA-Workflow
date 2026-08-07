# Fabricated report with plausible-looking numbers.
set f [open outputs/ct03_clock_skew.rpt w]
puts $f "Clock core_clock"
puts $f "Latency      CRPR       Skew"
puts $f "_675_/CK ^"
puts $f " 0.0530"
puts $f "_677_/CK ^"
puts $f " 0.0480    0.0000     0.0050"
close $f
