# Wrong: constraint defined after the pins were already placed (it has no effect).
place_pins -hor_layers metal3 -ver_layers metal2
set bus {}
for {set i 0} {$i < 32} {incr i} { lappend bus "req_msg\[$i\]" }
set_io_pin_constraint -region bottom:* -group -order -pin_names $bus
