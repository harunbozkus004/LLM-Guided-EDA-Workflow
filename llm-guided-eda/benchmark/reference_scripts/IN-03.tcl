# Cell usage per library cell, skipping physical-only cells (tap/endcap, filler).
set block [ord::get_db_block]
set usage [dict create]
foreach inst [$block getInsts] {
  set master [$inst getMaster]
  set type [$master getType]
  if {[$master isFiller] || $type in {CORE_WELLTAP CORE_SPACER} || [string match ENDCAP* $type]} {
    continue
  }
  dict incr usage [$master getName]
}
set total 0
set fh [open outputs/cell_usage.txt w]
foreach name [lsort [dict keys $usage]] {
  set n [dict get $usage $name]
  puts $fh "$name $n"
  incr total $n
}
puts $fh "total $total"
close $fh
