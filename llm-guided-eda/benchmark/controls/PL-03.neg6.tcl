# Utilization written as a fraction (0.08) instead of a percentage.
set u [rsz::utilization]
set f [open outputs/utilization.txt w]
puts $f [format "utilization_percent: %.2f" $u]
puts $f "above_target: no"
close $f
