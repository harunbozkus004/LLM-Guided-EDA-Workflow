# Alternative: level-by-level traversal, register pins from all_registers, tab-separated fields,
# library-qualified cell names.
set regck {}
foreach p [all_registers -clock_pins] { dict set regck [get_full_name $p] 1 }
set f [open outputs/ct06_clock_tree.txt w]
set frontier [list [get_nets clk]]
set level 1
while {[llength $frontier]} {
  set next {}
  foreach net $frontier {
    foreach pin [get_pins -quiet -of_objects $net -filter "direction==input"] {
      if {[dict exists $regck [get_full_name $pin]]} continue
      set cell [get_cells -of_objects $pin]
      set out [get_nets -of_objects [get_pins -of_objects $cell -filter "direction==output"]]
      set n 0
      foreach l [get_pins -quiet -of_objects $out -filter "direction==input"] { if {[dict exists $regck [get_full_name $l]]} { incr n } }
      puts $f "[get_full_name $cell]\t[get_full_name [get_property $cell liberty_cell]]\t$level\t$n"
      lappend next $out
    }
  }
  set frontier $next
  incr level
}
close $f
