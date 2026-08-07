# Alternative: STA view; the clock net is the net feeding the register clock pins.
set clock_nets {}
foreach pin [all_registers -clock_pins] {
  foreach net [get_nets -quiet -of_objects $pin] { lappend clock_nets [get_full_name $net] }
}
set clock_nets [lsort -unique $clock_nets]
set rows {}
foreach net [get_nets *] {
  set name [get_full_name $net]
  if {$name in $clock_nets || $name in {VDD VSS}} { continue }
  set fanout [llength [get_pins -quiet -of_objects $net -filter "direction==input"]]
  foreach port [get_ports -quiet -of_objects $net] {
    if {[get_property $port direction] eq "output"} { incr fanout }
  }
  lappend rows [list $name $fanout]
}
set fh [open outputs/high_fanout_nets.txt w]
foreach row [lrange [lsort -integer -decreasing -index 1 $rows] 0 4] { puts $fh [join $row "\t"] }
close $fh
