# Alternative: micron coordinates via ord::dbu_to_microns, lsort -command, displacement limit, tab separated.
proc by_disp {a b} { return [expr {[lindex $a 1] < [lindex $b 1] ? 1 : ([lindex $a 1] > [lindex $b 1] ? -1 : 0)}] }
set block [ord::get_db_block]
set cells {}
foreach inst [$block getInsts] {
  set m [$inst getMaster]
  if {[$m getType] ne "CORE"} continue
  set bb [$inst getBBox]
  lappend cells [list $inst [ord::dbu_to_microns [$bb xMin]] [ord::dbu_to_microns [$bb yMin]]]
}
detailed_placement -max_displacement {500 100}
check_placement
set res {}
foreach c $cells {
  lassign $c inst x0 y0
  set bb [$inst getBBox]
  set d [expr {abs([ord::dbu_to_microns [$bb xMin]] - $x0) + abs([ord::dbu_to_microns [$bb yMin]] - $y0)}]
  lappend res [list [$inst getName] $d]
}
set res [lsort -command by_disp $res]
set fh [open outputs/top_displaced.txt w]
foreach r [lrange $res 0 4] { puts $fh "[lindex $r 0]\t[format %.3f [lindex $r 1]]" }
close $fh
