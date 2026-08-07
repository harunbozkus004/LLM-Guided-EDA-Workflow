# Alternative: build with BUF_X8 everywhere, then downsize every non-root buffer.
clock_tree_synthesis -root_buf BUF_X8 -buf_list BUF_X2
set root_net [get_nets -of_objects [get_pins clkbuf_0_clk/Z]]
foreach pin [get_pins -of_objects $root_net -filter "direction==input"] {
  replace_cell [get_cells -of_objects $pin] BUF_X2
}
detailed_placement
