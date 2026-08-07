# Wrong: plain lsort is lexicographic (req_msg[0] req_msg[10] req_msg[11] ...), so the bus order is scrambled.
set names [lsort [lmap p [get_ports req_msg*] {get_full_name $p}]]
set_io_pin_constraint -region bottom:* -group -order -pin_names $names
place_pins -hor_layers metal3 -ver_layers metal2
