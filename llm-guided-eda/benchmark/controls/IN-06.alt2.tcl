# Alternative: walk each clock-tree buffer's output net and count register clock pins on it.
set ck_pins [all_registers -clock_pins]
set types [dict create]
foreach reg [all_registers -cells] { dict incr types [get_property $reg ref_name] }
set fh [open outputs/flop_clock_drivers.txt w]
foreach cell [get_cells *] {
  foreach out [get_pins -quiet -of_objects $cell -filter "direction==output"] {
    set n 0
    foreach load [get_pins -quiet -of_objects [get_nets -of_objects $out] -filter "direction==input"] {
      if {[lsearch -exact $ck_pins $load] >= 0} { incr n }
    }
    if {$n > 0} { puts $fh "[get_full_name $cell] $n" }
  }
}
close $fh
set fh [open outputs/flop_types.txt w]
dict for {ref n} $types { puts $fh "$ref $n" }
puts $fh "total [llength [all_registers -cells]]"
close $fh
