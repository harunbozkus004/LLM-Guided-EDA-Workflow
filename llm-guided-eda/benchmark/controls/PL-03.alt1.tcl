# Alternative: the resizer's utilization (design area / core area), after printing the area report.
report_design_area
set util [expr {100.0 * [rsz::utilization]}]
set f [open outputs/utilization.txt w]
puts $f "utilization_percent: [format %.2f $util]"
if {$util > 70} { puts $f "above_target: yes" } else { puts $f "above_target: no" }
close $f
