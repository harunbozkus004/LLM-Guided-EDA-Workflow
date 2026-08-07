# Alternative: mirroring optimization after legalization, skew parsed from a redirected
# 4-digit clock-skew report, buffers counted by the CTS naming convention.
clock_tree_synthesis -root_buf BUF_X4 -buf_list BUF_X4
detailed_placement
optimize_mirroring
check_placement
set_propagated_clock [get_clocks core_clock]
estimate_parasitics -placement
sta::redirect_file_begin outputs/skew.rpt
report_clock_skew -setup -clock core_clock -digits 4
sta::redirect_file_end
set fh [open outputs/skew.rpt]; set txt [read $fh]; close $fh
set skew [lindex [regexp -all -inline {\d+\.\d+} $txt] end]
set f [open outputs/ct05_cts_metrics.txt w]
puts $f "clock_buffers [llength [get_cells clkbuf_*]]"
puts $f "clock_skew_ns $skew"
close $f
