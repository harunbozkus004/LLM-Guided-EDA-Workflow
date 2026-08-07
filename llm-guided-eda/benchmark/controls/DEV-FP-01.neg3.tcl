# Wrong: pin names typed without the buses' bits (req_msg/resp_msg are not port names), so the buses go anywhere.
set_io_pin_constraint -pin_names {clk reset req_val resp_rdy} -region left:*
set_io_pin_constraint -pin_names {req_rdy resp_val} -region right:*
place_pins -hor_layers metal3 -ver_layers metal2
