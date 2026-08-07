# Wrong object: get_cells -of_objects on the clock net returns every cell on it, flip-flops included.
set types [dict create]
foreach reg [all_registers -cells] { dict incr types [get_property $reg ref_name] }
set drivers [dict create]
foreach ck [all_registers -clock_pins] {
  foreach cell [get_cells -of_objects [get_nets -of_objects $ck]] { dict incr drivers [get_full_name $cell] }
}
set fh [open outputs/flop_types.txt w]
dict for {ref n} $types { puts $fh "$ref $n" }
puts $fh "total [llength [all_registers -cells]]"
close $fh
set fh [open outputs/flop_clock_drivers.txt w]
dict for {inst n} $drivers { puts $fh "$inst $n" }
close $fh
