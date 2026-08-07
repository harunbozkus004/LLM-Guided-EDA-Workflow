# Alternative: STA object queries instead of the database API; deepest level first.
proc walk {net level} {
  set rows {}
  foreach pin [get_pins -quiet -of_objects $net -filter "direction==input"] {
    set cell [get_cells -of_objects $pin]
    if {[get_property [get_property $cell liberty_cell] is_buffer]} {
      set out [get_nets -of_objects [get_pins -of_objects $cell -filter "direction==output"]]
      set n_reg 0
      foreach load [get_pins -quiet -of_objects $out -filter "direction==input"] {
        if {[get_property $load is_register_clock]} { incr n_reg }
      }
      lappend rows [list [get_full_name $cell] [get_property $cell ref_name] $level $n_reg]
      set rows [concat $rows [walk $out [expr {$level + 1}]]]
    }
  }
  return $rows
}
set rows [walk [get_nets clk] 1]
set f [open outputs/ct06_clock_tree.txt w]
foreach r [lsort -integer -decreasing -index 2 $rows] { puts $f [join $r " "] }
close $f
