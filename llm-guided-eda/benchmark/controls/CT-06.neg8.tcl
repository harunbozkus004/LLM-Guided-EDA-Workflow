# Incomplete: only the leaf buffers that drive registers are listed (root buffer missing).
set f [open outputs/ct06_clock_tree.txt w]
foreach cell [get_cells clkbuf_*_f_clk] {
  set n 0
  foreach l [get_pins -quiet -of_objects [get_nets -of_objects [get_pins [get_full_name $cell]/Z]] -filter "direction==input"] {
    if {[get_property $l is_register_clock]} { incr n }
  }
  puts $f "[get_full_name $cell] [get_property $cell ref_name] 2 $n"
}
close $f
