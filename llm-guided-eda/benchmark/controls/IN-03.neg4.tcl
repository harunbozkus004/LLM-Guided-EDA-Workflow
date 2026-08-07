# Inconsistent: per-type rows skip the tap cells, but the total is the instance count of the whole design.
set usage [dict create]
foreach cell [get_cells *] {
  set ref [get_property $cell ref_name]
  if {[string match TAPCELL* $ref]} { continue }
  dict incr usage $ref
}
set fh [open outputs/cell_usage.txt w]
dict for {ref n} $usage { puts $fh "$ref $n" }
puts $fh "total [llength [get_cells *]]"
close $fh
