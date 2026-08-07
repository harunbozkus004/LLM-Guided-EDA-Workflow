# Wrong: physical-only tap cells are counted as well.
set usage [dict create]
foreach cell [get_cells *] { dict incr usage [get_property $cell ref_name] }
set total 0
set fh [open outputs/cell_usage.txt w]
dict for {ref n} $usage { puts $fh "$ref $n"; incr total $n }
puts $fh "total $total"
close $fh
