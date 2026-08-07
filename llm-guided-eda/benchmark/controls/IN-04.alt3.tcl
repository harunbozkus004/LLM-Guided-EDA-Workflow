# Alternative: STA; the clock net is the one feeding the flip-flop CK pins, output ports counted via all_outputs.
set clock_nets [lsort -unique [lmap p [get_pins */CK] {get_full_name [get_nets -of_objects $p]}]]
set out_ports [lmap p [all_outputs] {get_full_name $p}]
set rows {}
foreach net [get_nets *] {
  set name [get_full_name $net]
  if {$name in $clock_nets || $name in {VDD VSS}} { continue }
  set n [llength [get_pins -quiet -of_objects $net -filter "direction==input"]]
  foreach port [get_ports -quiet -of_objects $net] {
    if {[get_full_name $port] in $out_ports} { incr n }
  }
  lappend rows [list $name $n]
}
set rows [lsort -integer -decreasing -index 1 $rows]
set fh [open outputs/high_fanout_nets.txt w]
for {set i 0} {$i < 5} {incr i} { puts $fh "[lindex $rows $i 0]: [lindex $rows $i 1]" }
close $fh
