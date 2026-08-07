# Mirrors every cell about the Y axis, regardless of the effect on wirelength.
array set mirror_y {R0 MY MY R0 MX R180 R180 MX}
foreach inst [[ord::get_db_block] getInsts] {
  if {[[$inst getMaster] getType] ne "CORE"} continue
  lassign [$inst getLocation] x y
  $inst setOrient $mirror_y([$inst getOrient])
  $inst setLocation $x $y
}
