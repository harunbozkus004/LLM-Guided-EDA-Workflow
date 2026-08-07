# Missing prerequisite: skew measured without parasitic estimation.
clock_tree_synthesis -root_buf BUF_X4 -buf_list BUF_X4
detailed_placement
set_propagated_clock [all_clocks]
set f [open outputs/ct05_cts_metrics.txt w]
puts $f "clock_buffers [llength [get_cells clkbuf_*]]"
puts $f [format "clock_skew_ns %.4f" [sta::worst_clock_skew -setup]]
close $f
