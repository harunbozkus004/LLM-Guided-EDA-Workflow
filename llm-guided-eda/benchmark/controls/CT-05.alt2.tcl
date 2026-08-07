# Alternative: flow-style sequence, skew parsed from a report file, STA-based buffer count.
clock_tree_synthesis -root_buf BUF_X4 -buf_list BUF_X4 -sink_clustering_enable
set_propagated_clock [all_clocks]
repair_clock_nets
detailed_placement
estimate_parasitics -placement
report_clock_skew -setup -digits 4 > outputs/skew.rpt
set fh [open outputs/skew.rpt r]
set lines [split [string trim [read $fh]] "\n"]
close $fh
set skew [lindex [lindex $lines end] end]
set n_buf 0
foreach net [get_nets {clk clknet_*}] {
  foreach pin [get_pins -quiet -of_objects $net -filter "direction==input"] {
    if {[get_property [get_property [get_cells -of_objects $pin] liberty_cell] is_buffer]} { incr n_buf }
  }
}
set f [open outputs/ct05_cts_metrics.txt w]
puts $f "clock_buffers $n_buf"
puts $f "clock_skew_ns $skew"
close $f
