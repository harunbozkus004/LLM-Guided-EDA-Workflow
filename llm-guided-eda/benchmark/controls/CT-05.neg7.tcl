# Version pitfall: parasitics first estimated while the clock is ideal, then propagated-clock
# timing computed before re-estimating. The re-estimation does not add the clock-tree wire RC,
# so the clock nets still have no parasitics and the reported skew is ~0.0018 ns.
clock_tree_synthesis -root_buf BUF_X4 -buf_list BUF_X4
detailed_placement
estimate_parasitics -placement
set_propagated_clock [all_clocks]
report_checks
estimate_parasitics -placement
set f [open outputs/ct05_cts_metrics.txt w]
puts $f "clock_buffers [llength [get_cells clkbuf_*]]"
puts $f [format "clock_skew_ns %.6f" [sta::worst_clock_skew -setup]]
close $f
