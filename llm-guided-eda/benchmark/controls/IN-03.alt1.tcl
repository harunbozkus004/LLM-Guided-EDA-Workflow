# Alternative: STA instances and their library cells; physical-only cells recognized by name.
set usage [dict create]
foreach cell [get_cells *] {
  set ref [get_property $cell ref_name]
  if {[string match TAPCELL* $ref] || [string match FILLCELL* $ref]} { continue }
  dict incr usage $ref
}
set fh [open outputs/cell_usage.txt w]
puts $fh "# cell usage (logic cells only)"
dict for {ref n} $usage { puts $fh [format "%-12s %5d" $ref $n] }
puts $fh "total [tcl::mathop::+ {*}[dict values $usage]]"
close $fh
