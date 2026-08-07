# Wrong count: every input pin on the output net counted, so the root reports its 4 buffer loads.
set f [open outputs/ct06_clock_tree.txt w]
foreach cell [get_cells clkbuf_*] {
  set name [get_full_name $cell]
  set level [expr {$name eq "clkbuf_0_clk" ? 1 : 2}]
  set out [get_nets -of_objects [get_pins $name/Z]]
  puts $f "$name [get_property $cell ref_name] $level [llength [get_pins -of_objects $out -filter direction==input]]"
}
close $f
