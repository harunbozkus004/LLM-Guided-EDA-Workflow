# Alternative: loop over the liberty cells and count instances of each; tap cells have no liberty model.
set total 0
set fh [open outputs/cell_usage.txt w]
foreach lib_cell [get_lib_cells *] {
  set name [get_name $lib_cell]
  set n [llength [get_cells -quiet -filter "ref_name==$name" *]]
  if {$n == 0} { continue }
  puts $fh "$name $n"
  incr total $n
}
puts $fh "total $total"
close $fh
