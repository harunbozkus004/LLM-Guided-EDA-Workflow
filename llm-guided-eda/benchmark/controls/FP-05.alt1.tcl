# Alternative: bit-ordered list from a dictionary sort of the port names, annealing pin placer.
set names [lsort -dictionary [lmap p [get_ports req_msg*] {get_full_name $p}]]
set_io_pin_constraint -pin_names $names -region bottom:* -group -order
place_pins -hor_layers metal3 -ver_layers metal2 -annealing
