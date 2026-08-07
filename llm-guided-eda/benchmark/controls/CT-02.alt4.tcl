# Alternative: hand-written summary with explanatory remarks after each value (the buffers line
# also mentions "root"), values computed from the netlist.
clock_tree_synthesis -root_buf BUF_X8 -buf_list BUF_X8
set leaf [get_cells clkbuf_*_f_clk]
set all [get_cells clkbuf_*]
set f [open outputs/ct02_cts_summary.txt w]
puts $f "Clock roots: [llength [get_ports clk]] (port clk)"
puts $f "Clock buffers inserted: [llength $all] (1 root + [llength $leaf] leaf, BUF_X8)"
puts $f "Clock subnets: [llength [get_nets clknet_*]] (nets driven by the clock buffers)"
puts $f "Clock sinks: [llength [all_registers -clock_pins]] register clock pins"
close $f
