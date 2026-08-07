# Order pitfall: parasitics estimated while the clock is still ideal, so the
# clock-tree nets get no wire parasitics; the clock is propagated afterwards.
clock_tree_synthesis -root_buf BUF_X4 -buf_list BUF_X4
detailed_placement
estimate_parasitics -placement
set_propagated_clock [all_clocks]
with_output_to_variable rpt { report_clock_skew -setup -digits 4 }
set skew [lindex $rpt end]
set f [open outputs/ct05_cts_metrics.txt w]
puts $f "clock_buffers [llength [get_cells clkbuf_*]]"
puts $f "clock_skew_ns $skew"
close $f
