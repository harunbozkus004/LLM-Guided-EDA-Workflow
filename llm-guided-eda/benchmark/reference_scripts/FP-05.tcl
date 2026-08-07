# req_msg bus on the bottom edge, grouped and ordered by bit index; all other pins anywhere.
set bus {}
for {set i 0} {$i < 32} {incr i} { lappend bus "req_msg\[$i\]" }
set_io_pin_constraint -region bottom:* -group -order -pin_names $bus
place_pins -hor_layers metal3 -ver_layers metal2
