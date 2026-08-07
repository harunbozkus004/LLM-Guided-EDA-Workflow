# Displacement left in database units instead of microns.
set block [ord::get_db_block]
foreach inst [$block getInsts] {
  if {[[$inst getMaster] getType] ne "CORE"} continue
  set before([$inst getName]) [$inst getLocation]
}
detailed_placement
set disp {}
foreach name [array names before] {
  lassign $before($name) x0 y0
  lassign [[$block findInst $name] getLocation] x1 y1
  lappend disp [list $name [expr {abs($x1 - $x0) + abs($y1 - $y0)}]]
}
set f [open outputs/top_displaced.txt w]
foreach item [lrange [lsort -real -decreasing -index 1 $disp] 0 4] {
  puts $f [format "%s %.3f" [lindex $item 0] [lindex $item 1]]
}
close $f
