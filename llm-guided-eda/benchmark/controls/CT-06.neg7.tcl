# Misread sink count: registers counted transitively (the root reports all 35 instead of 0).
proc walk {net level} {
  set rows {}; set total 0
  foreach pin [get_pins -quiet -of_objects $net -filter "direction==input"] {
    if {[get_property $pin is_register_clock]} { incr total; continue }
    set cell [get_cells -of_objects $pin]
    set out [get_nets -of_objects [get_pins -of_objects $cell -filter "direction==output"]]
    lassign [walk $out [expr {$level + 1}]] sub n
    lappend rows [list [get_full_name $cell] [get_property $cell ref_name] $level $n]
    set rows [concat $rows $sub]
    incr total $n
  }
  return [list $rows $total]
}
lassign [walk [get_nets clk] 1] rows total
set f [open outputs/ct06_clock_tree.txt w]
foreach r $rows { puts $f [join $r " "] }
close $f
