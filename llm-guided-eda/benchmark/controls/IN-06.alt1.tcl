# Alternative: OpenDB traversal; flip-flops recognized by their library cell names (Nangate45 *DFF*).
set block [ord::get_db_block]
set types [dict create]
set drivers [dict create]
foreach inst [$block getInsts] {
  set master [[$inst getMaster] getName]
  if {![string match *DFF* $master]} { continue }
  dict incr types $master
  set net [[$inst findITerm CK] getNet]
  foreach iterm [$net getITerms] {
    if {[$iterm getIoType] eq "OUTPUT"} { dict incr drivers [[$iterm getInst] getName] }
  }
}
set fh [open outputs/flop_types.txt w]
foreach ref [lsort [dict keys $types]] { puts $fh [format "%-8s %3d" $ref [dict get $types $ref]] }
puts $fh [format "%-8s %3d" total [tcl::mathop::+ {*}[dict values $types]]]
close $fh
set fh [open outputs/flop_clock_drivers.txt w]
foreach inst [lsort [dict keys $drivers]] { puts $fh "$inst\t[dict get $drivers $inst]" }
puts $fh "total\t[tcl::mathop::+ {*}[dict values $drivers]]"
close $fh
