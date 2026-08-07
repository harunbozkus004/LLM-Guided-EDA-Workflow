# Alternative: region constraint for the bus plus an ordered pin group given to place_pins.
set bus {}
for {set i 0} {$i < 32} {incr i} { lappend bus "req_msg\[$i\]" }
set_io_pin_constraint -region bottom:* -pin_names $bus
place_pins -hor_layers metal3 -ver_layers metal2 -group_pins $bus
