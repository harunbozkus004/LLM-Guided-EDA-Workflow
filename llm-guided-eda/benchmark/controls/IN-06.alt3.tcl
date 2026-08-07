# Alternative: flip-flops selected by library-cell name filter, clock pins by the Nangate45 pin name CK.
set types [dict create]
foreach reg [get_cells -filter "ref_name=~DFF*" *] { dict incr types [get_property $reg ref_name] }
set drivers [dict create]
foreach ck [get_pins */CK] {
  set drv [get_pins -quiet -of_objects [get_nets -of_objects $ck] -filter "direction==output"]
  foreach d $drv { dict incr drivers [get_full_name [get_cells -of_objects $d]] }
}
set fh [open outputs/flop_types.txt w]
dict for {ref n} $types { puts $fh "$ref: $n" }
puts $fh "total: [tcl::mathop::+ {*}[dict values $types]]"
close $fh
set fh [open outputs/flop_clock_drivers.txt w]
dict for {inst n} $drivers { puts $fh "$inst: $n" }
close $fh
