# Blueprint task 5: CTS with the SDC clock, legalization, clock-tree metrics.
clock_tree_synthesis -root_buf BUF_X4 -buf_list BUF_X4
detailed_placement

# Propagate first: parasitics estimated while the clock is ideal skip the clock nets.
set_propagated_clock [all_clocks]
estimate_parasitics -placement

# Clock buffers: walk the clock network from the clk port to the register clock pins.
set block [ord::get_db_block]
set queue [list [[$block findBTerm clk] getNet]]
set n_buf 0
while {[llength $queue]} {
  set net [lindex $queue 0]
  set queue [lrange $queue 1 end]
  foreach it [$net getITerms] {
    if {![$it isInputSignal]} { continue }
    set inst [$it getInst]
    # Registers (DFF_X1/DFF_X2) are the sinks; every other load is a clock-tree cell.
    if {[string match DFF* [[$inst getMaster] getName]]} { continue }
    incr n_buf
    foreach ot [$inst getITerms] {
      if {[$ot isOutputSignal] && [$ot getNet] ne "NULL"} { lappend queue [$ot getNet] }
    }
  }
}

# Worst setup skew: the last number of the STA clock-skew report.
with_output_to_variable skew_rpt { report_clock_skew -setup -digits 6 }
set skew [lindex [regexp -all -inline {[-+]?[0-9]*\.[0-9]+} $skew_rpt] end]

set f [open outputs/ct05_cts_metrics.txt w]
puts $f "clock_buffers $n_buf"
puts $f [format "clock_skew_ns %.6f" $skew]
close $f
