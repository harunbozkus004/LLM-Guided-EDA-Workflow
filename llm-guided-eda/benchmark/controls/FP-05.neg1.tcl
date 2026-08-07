# Wrong: glob pattern with -group (the group is ignored with a warning), so the bits are not ordered.
set_io_pin_constraint -region bottom:* -group -order -pin_names {req_msg*}
place_pins -hor_layers metal3 -ver_layers metal2
