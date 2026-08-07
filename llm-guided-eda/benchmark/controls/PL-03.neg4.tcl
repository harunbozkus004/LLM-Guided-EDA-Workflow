# Correct value but compared against the target as a fraction (0.70) -> wrong decision.
set util [expr {100.0 * [rsz::utilization]}]
set f [open outputs/utilization.txt w]
puts $f [format "utilization_percent: %.2f" $util]
puts $f "above_target: [expr {$util > 0.70 ? "yes" : "no"}]"
close $f
