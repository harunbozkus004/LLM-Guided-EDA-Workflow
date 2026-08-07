# Correct metrics for the unlegalized design, but the clock buffers are never legalized.
clock_tree_synthesis -root_buf BUF_X4 -buf_list BUF_X4
set_propagated_clock [all_clocks]
estimate_parasitics -placement
set f [open outputs/ct05_cts_metrics.txt w]
puts $f "clock_buffers [llength [get_cells clkbuf_*]]"
puts $f [format "clock_skew_ns %.4f" [sta::worst_clock_skew -setup]]
close $f
