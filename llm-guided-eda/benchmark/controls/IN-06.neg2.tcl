# Wrong: reports the full fanout of every clock buffer, so the root buffer (driving only buffers) is listed.
set types [dict create]
foreach reg [all_registers -cells] { dict incr types [get_property $reg ref_name] }
set total 0
set fh [open outputs/flop_types.txt w]
dict for {ref n} $types { puts $fh "$ref $n"; incr total $n }
puts $fh "total $total"
close $fh
set fh [open outputs/flop_clock_drivers.txt w]
foreach buf [get_cells clkbuf*] {
  set out [get_pins -of_objects $buf -filter "direction==output"]
  set loads [get_pins -of_objects [get_nets -of_objects $out] -filter "direction==input"]
  puts $fh "[get_full_name $buf] [llength $loads]"
}
close $fh
