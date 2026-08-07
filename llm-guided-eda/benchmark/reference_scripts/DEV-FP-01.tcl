# Inputs on the left edge, outputs on the right edge.
set_io_pin_constraint -direction INPUT -region left:*
set_io_pin_constraint -direction OUTPUT -region right:*
place_pins -hor_layers metal3 -ver_layers metal2
