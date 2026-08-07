# Alternative: clock propagated before CTS, parasitics estimated before legalization (stale by
# ~3.5e-5 ns, within the rounding tolerance), "key: value" lines and 4-digit skew.
set_propagated_clock [all_clocks]
clock_tree_synthesis -root_buf BUF_X4 -buf_list BUF_X4
estimate_parasitics -placement
detailed_placement
estimate_parasitics -placement
report_clock_skew -setup -digits 4
set n_buf [llength [get_cells -filter "ref_name == BUF_X4" *]]
set f [open outputs/ct05_cts_metrics.txt w]
puts $f "clock_buffers: $n_buf"
puts $f [format "clock_skew_ns: %.4f" [sta::worst_clock_skew -setup]]
close $f
