# Wrong fanout definition: every pin on the net is counted, including the driver.
set rows {}
foreach net [get_nets *] {
  set name [get_full_name $net]
  if {$name eq "clk"} { continue }
  lappend rows [list $name [llength [get_pins -quiet -of_objects $net]]]
}
set fh [open outputs/high_fanout_nets.txt w]
foreach row [lrange [lsort -integer -decreasing -index 1 $rows] 0 4] { puts $fh [join $row " "] }
close $fh
