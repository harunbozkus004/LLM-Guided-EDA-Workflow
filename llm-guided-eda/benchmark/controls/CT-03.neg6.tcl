# Incomplete report: only the skew value, the two register clock pins are not named.
estimate_parasitics -placement
set f [open outputs/ct03_clock_skew.rpt w]
puts $f [format "core_clock setup skew %.4f" [sta::worst_clock_skew -setup]]
close $f
