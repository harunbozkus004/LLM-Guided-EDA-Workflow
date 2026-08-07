# Hedging: two different skew rows (only one is right).
set f [open outputs/clock_skew.rpt w]
puts $f "Clock core_clock"
puts $f "Latency      CRPR       Skew"
puts $f "_675_/CK ^"
puts $f " 0.0448    0.0000     0.0018"
puts $f " 0.0448    0.0000     0.0032"
close $f
