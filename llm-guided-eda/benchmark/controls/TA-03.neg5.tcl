# Unit mistake: skew converted to ps although the task asks for ns.
set f [open outputs/clock_skew.rpt w]
puts $f [format "core_clock setup skew %.4f ps" [expr {[worst_clock_skew -setup] * 1000.0}]]
close $f
