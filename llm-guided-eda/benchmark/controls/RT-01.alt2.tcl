# Alternative: route, then dump the stored guides in route-guide format by hand (DBU coordinates).
global_route -allow_congestion
set fh [open outputs/gcd.guide w]
foreach net [[ord::get_db_block] getNets] {
  set guides [$net getGuides]
  if {[llength $guides] == 0} { continue }
  puts $fh [$net getName]
  puts $fh "("
  foreach g $guides {
    set b [$g getBox]
    puts $fh "[$b xMin] [$b yMin] [$b xMax] [$b yMax] [[$g getLayer] getName]"
  }
  puts $fh ")"
}
close $fh
