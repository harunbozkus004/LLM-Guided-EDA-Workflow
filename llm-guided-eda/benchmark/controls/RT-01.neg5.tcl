# Mistake: hand-written guide dump with coordinates in micrometers instead of database units.
global_route
set block [ord::get_db_block]
set dbu [$block getDefUnits]
set fh [open outputs/gcd.guide w]
foreach net [$block getNets] {
  set guides [$net getGuides]
  if {[llength $guides] == 0} { continue }
  puts $fh [$net getName]
  puts $fh "("
  foreach g $guides {
    set b [$g getBox]
    puts $fh "[expr {[$b xMin] / double($dbu)}] [expr {[$b yMin] / double($dbu)}] [expr {[$b xMax] / double($dbu)}] [expr {[$b yMax] / double($dbu)}] [[$g getLayer] getName]"
  }
  puts $fh ")"
}
close $fh
