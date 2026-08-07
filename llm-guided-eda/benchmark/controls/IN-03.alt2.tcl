# Alternative: keep only masters of class CORE (tap cells are CORE_WELLTAP), Tcl arrays.
set block [ord::get_db_block]
array set usage {}
set total 0
foreach inst [$block getInsts] {
  set master [$inst getMaster]
  if {[$master getType] ne "CORE"} { continue }
  set name [$master getName]
  if {![info exists usage($name)]} { set usage($name) 0 }
  incr usage($name)
  incr total
}
set fh [open outputs/cell_usage.txt w]
foreach name [lsort -dictionary [array names usage]] { puts $fh "$name\t$usage($name)" }
puts $fh "total\t$total"
close $fh
