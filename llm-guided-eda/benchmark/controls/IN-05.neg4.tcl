# Wrong units: raw resizer values (square meters and a fraction) written without conversion.
set util [rsz::utilization]
set area [rsz::design_area]
set fh [open outputs/floorplan_summary.txt w]
puts $fh "die_area [join [lmap v [ord::get_die_area] {format %.2f $v}] { }]"
puts $fh "core_area [join [lmap v [ord::get_core_area] {format %.2f $v}] { }]"
puts $fh "cell_area $area"
puts $fh "utilization $util"
close $fh
