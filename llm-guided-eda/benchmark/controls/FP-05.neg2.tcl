# Wrong: port collection order is req_msg[31] ... req_msg[0], so the bus ends up reversed.
set names [lmap p [get_ports req_msg*] {get_full_name $p}]
set_io_pin_constraint -region bottom:* -group -order -pin_names $names
place_pins -hor_layers metal3 -ver_layers metal2
