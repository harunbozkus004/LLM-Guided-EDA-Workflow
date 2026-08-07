# Wrong: the clock net is not excluded.
set rows {}
foreach net [get_nets *] {
  set fanout [llength [get_pins -quiet -of_objects $net -filter "direction==input"]]
  foreach port [get_ports -quiet -of_objects $net] {
    if {[get_property $port direction] eq "output"} { incr fanout }
  }
  lappend rows [list [get_full_name $net] $fanout]
}
set fh [open outputs/high_fanout_nets.txt w]
foreach row [lrange [lsort -integer -decreasing -index 1 $rows] 0 4] { puts $fh [join $row " "] }
close $fh
