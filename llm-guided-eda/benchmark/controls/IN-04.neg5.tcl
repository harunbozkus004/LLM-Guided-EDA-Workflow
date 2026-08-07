# Incomplete fanout: only cell input pins are counted, the top-level output port sink is ignored.
set rows {}
foreach net [get_nets *] {
  set name [get_full_name $net]
  if {$name in {clk VDD VSS}} { continue }
  lappend rows [list $name [llength [get_pins -quiet -of_objects $net -filter "direction==input"]]]
}
set fh [open outputs/high_fanout_nets.txt w]
foreach row [lrange [lsort -integer -decreasing -index 1 $rows] 0 4] { puts $fh [join $row " "] }
close $fh
