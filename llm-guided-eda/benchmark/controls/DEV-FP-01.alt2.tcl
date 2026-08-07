# Alternative: explicit edge intervals spanning the whole die side.
lassign [ord::get_die_area] x0 y0 x1 y1
set_io_pin_constraint -direction INPUT -region "left:$y0-$y1"
set_io_pin_constraint -direction OUTPUT -region "right:$y0-$y1"
place_pins -hor_layers metal3 -ver_layers metal2 -min_distance 1
