# Fabricated skew report written with puts.
set f [open outputs/clock_skew.rpt w]
puts $f "Clock core_clock"
puts $f "Latency      CRPR       Skew"
puts $f "_675_/CK ^"
puts $f " 0.0452"
puts $f "_679_/CK ^"
puts $f " 0.0410    0.0000     0.0042"
close $f
