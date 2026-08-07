# Skew parsed from the default 2-digit clock-skew report (0.00) instead of >= 4 digits.
clock_tree_synthesis -root_buf BUF_X4 -buf_list BUF_X4
detailed_placement
set_propagated_clock [all_clocks]
estimate_parasitics -placement
with_output_to_variable rpt { report_clock_skew -setup }
set f [open outputs/ct05_cts_metrics.txt w]
puts $f "clock_buffers [llength [get_cells clkbuf_*]]"
puts $f "clock_skew_ns [lindex $rpt end]"
close $f
