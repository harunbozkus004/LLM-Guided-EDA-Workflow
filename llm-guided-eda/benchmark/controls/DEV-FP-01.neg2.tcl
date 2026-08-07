# Wrong: edges swapped.
set_io_pin_constraint -direction INPUT -region right:*
set_io_pin_constraint -direction OUTPUT -region left:*
place_pins -hor_layers metal3 -ver_layers metal2
