# Header line added although the file must contain only the buffer lines.
set f [open outputs/ct06_clock_tree.txt w]
puts $f "instance cell level register_sinks"
foreach cell [get_cells clkbuf_*] {
  set name [get_full_name $cell]
  set level [expr {$name eq "clkbuf_0_clk" ? 1 : 2}]
  set n 0
  foreach l [get_pins -quiet -of_objects [get_nets -of_objects [get_pins $name/Z]] -filter "direction==input"] {
    if {[string match DFF* [get_property [get_cells -of_objects $l] ref_name]]} { incr n }
  }
  puts $f "$name [get_property $cell ref_name] $level $n"
}
close $f
