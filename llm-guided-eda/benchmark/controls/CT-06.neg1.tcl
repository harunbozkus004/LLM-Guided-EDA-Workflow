# Off by one: every pin on the output net is counted (driver and buffer loads included).
set f [open outputs/ct06_clock_tree.txt w]
foreach cell [get_cells clkbuf_*] {
  set name [get_full_name $cell]
  set level [expr {$name eq "clkbuf_0_clk" ? 1 : 2}]
  set out [get_nets -of_objects [get_pins $name/Z]]
  puts $f "$name [get_property $cell ref_name] $level [llength [get_pins -of_objects $out]]"
}
close $f
