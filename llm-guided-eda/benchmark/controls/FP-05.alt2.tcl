# Alternative: place each bus bit explicitly on metal2 tracks of the bottom edge, then the rest.
for {set i 0} {$i < 32} {incr i} {
  set x [expr {20.095 + 1.9 * $i}]
  place_pin -pin_name "req_msg\[$i\]" -layer metal2 -location [list $x 0] -force_to_die_boundary
}
place_pins -hor_layers metal3 -ver_layers metal2
