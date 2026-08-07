# Flip-flops by cell type, and the cells that drive their clock pins.
set types [dict create]
foreach reg [all_registers -edge_triggered -cells] {
  dict incr types [get_property $reg ref_name]
}
set drivers [dict create]
foreach ck_pin [all_registers -edge_triggered -clock_pins] {
  foreach net [get_nets -quiet -of_objects $ck_pin] {
    foreach drv [get_pins -quiet -of_objects $net -filter "direction==output"] {
      dict incr drivers [get_full_name [get_cells -of_objects $drv]]
    }
  }
}
set total 0
set fh [open outputs/flop_types.txt w]
dict for {ref n} $types {
  puts $fh "$ref $n"
  incr total $n
}
puts $fh "total $total"
close $fh
set fh [open outputs/flop_clock_drivers.txt w]
dict for {inst n} $drivers { puts $fh "$inst $n" }
close $fh
