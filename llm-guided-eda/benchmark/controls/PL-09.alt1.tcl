# Alternative: flow-style padded legalization; positions taken from bounding boxes in a dict.
set block [ord::get_db_block]
set start [dict create]
foreach inst [$block getInsts] {
  set m [$inst getMaster]
  if {[$m isFiller] || [$m getType] eq "CORE_WELLTAP"} continue
  set bb [$inst getBBox]
  dict set start [$inst getName] [list [$bb xMin] [$bb yMin]]
}
set_placement_padding -global -left 1 -right 1
detailed_placement
check_placement
set rows {}
dict for {name xy} $start {
  set bb [[$block findInst $name] getBBox]
  set d [expr {abs([$bb xMin] - [lindex $xy 0]) + abs([$bb yMin] - [lindex $xy 1])}]
  lappend rows [list $name [expr {$d / 2000.0}]]
}
set rows [lsort -decreasing -real -index 1 $rows]
set out [open outputs/top_displaced.txt w]
for {set i 0} {$i < 5} {incr i} {
  lassign [lindex $rows $i] name d
  puts $out "$name [format %.3f $d]"
}
close $out
