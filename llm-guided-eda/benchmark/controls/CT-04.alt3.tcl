# Alternative: root buffer found through STA queries (buffer loads of the clk net), then legalized.
clock_tree_synthesis -buf_list BUF_X2
set root_pins [get_pins -of_objects [get_nets clk] -filter "direction==input"]
foreach p $root_pins {
  set inst [get_cells -of_objects $p]
  if {[get_property [get_property $inst liberty_cell] is_buffer]} { replace_cell $inst BUF_X8 }
}
detailed_placement
check_placement -verbose
