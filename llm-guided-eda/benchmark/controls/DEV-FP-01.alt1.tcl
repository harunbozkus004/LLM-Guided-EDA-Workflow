# Alternative: constraints by pin name.
set_io_pin_constraint -pin_names {clk reset req_val resp_rdy req_msg*} -region left:*
set_io_pin_constraint -pin_names {req_rdy resp_val resp_msg*} -region right:*
place_pins -hor_layers metal3 -ver_layers metal2
