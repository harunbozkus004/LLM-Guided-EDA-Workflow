# Alternative: buffers found by the CTS naming convention, levels from the driver chain.
set f [open outputs/ct06_clock_tree.txt w]
foreach cell [lsort [get_cells clkbuf_*]] {
  set name [get_full_name $cell]
  set level 1
  set drv_net [get_nets -of_objects [get_pins $name/A]]
  while {[get_full_name $drv_net] ne "clk"} {
    incr level
    set drv [get_pins -of_objects $drv_net -filter "direction==output"]
    set drv_net [get_nets -of_objects [get_pins [get_full_name [get_cells -of_objects $drv]]/A]]
  }
  set n_reg 0
  foreach load [get_pins -quiet -of_objects [get_nets -of_objects [get_pins $name/Z]] -filter "direction==input"] {
    if {[string match DFF* [get_property [get_cells -of_objects $load] ref_name]]} { incr n_reg }
  }
  puts $f "$name [get_property $cell ref_name] $level $n_reg"
}
close $f
