# Alternative: hand-written summary in key=value / key: value form, values from the netlist.
clock_tree_synthesis -root_buf BUF_X8 -buf_list BUF_X8
set bufs [get_cells -of_objects [get_pins -of_objects [get_nets clk] -filter "direction==input"]]
set subnets {}
foreach b [get_cells clkbuf_*] { lappend subnets [get_nets -of_objects [get_pins -of_objects $b -filter "direction==output"]] }
set f [open outputs/ct02_cts_summary.txt w]
puts $f "roots=[llength [get_ports clk]]"
puts $f "buffers: [llength [get_cells clkbuf_*]]"
puts $f "subnets=[llength $subnets]"
puts $f "sinks: [llength [all_registers -clock_pins]]"
close $f
