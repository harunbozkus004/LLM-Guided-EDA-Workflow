# Wrong subnet count: the clk port net is counted as a clock subnet as well (6 instead of 5).
clock_tree_synthesis -root_buf BUF_X8 -buf_list BUF_X8
set f [open outputs/ct02_cts_summary.txt w]
puts $f "roots 1"
puts $f "buffers [llength [get_cells clkbuf_*]]"
puts $f "subnets [llength [get_nets {clk clknet_*}]]"
puts $f "sinks [llength [all_registers -clock_pins]]"
close $f
