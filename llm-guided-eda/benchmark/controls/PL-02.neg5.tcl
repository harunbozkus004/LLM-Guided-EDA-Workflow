# Hand-written legalizer: snaps every cell to the nearest row/site without resolving overlaps.
set block [ord::get_db_block]
set rows [$block getRows]
set sw [[[lindex $rows 0] getSite] getWidth]
foreach inst [$block getInsts] {
  if {[[$inst getMaster] getType] ne "CORE"} continue
  lassign [$inst getLocation] x y
  set best ""; set bd 1e30
  foreach r $rows { set d [expr {abs([[$r getBBox] yMin] - $y)}]; if {$d < $bd} { set bd $d; set best $r } }
  set x0 [[$best getBBox] xMin]
  set nx [expr {$x0 + round(double($x - $x0) / $sw) * $sw}]
  $inst setOrient [$best getOrient]
  $inst setLocation $nx [[$best getBBox] yMin]
}
