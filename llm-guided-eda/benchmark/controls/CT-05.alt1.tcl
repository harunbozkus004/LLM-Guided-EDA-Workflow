# Alternative: buffer count from the CTS summary report, skew from the STA API.
clock_tree_synthesis -buf_list BUF_X4
report_cts -out_file outputs/cts_summary.txt
detailed_placement
set_propagated_clock [get_clocks core_clock]
estimate_parasitics -placement
set fh [open outputs/cts_summary.txt r]
set txt [read $fh]
close $fh
regexp {Buffers Inserted:\s*(\d+)} $txt -> n_buf
set f [open outputs/ct05_cts_metrics.txt w]
puts $f "clock_buffers $n_buf"
puts $f [format "clock_skew_ns %.4f" [sta::worst_clock_skew -setup]]
close $f
