# Alternative: compute the summary metrics by inspecting the netlist.
clock_tree_synthesis -root_buf BUF_X8 -buf_list BUF_X8
set block [ord::get_db_block]
set queue [list [[$block findBTerm clk] getNet]]
set n_buf 0; set n_subnets 0; set n_sinks 0; set first 1
while {[llength $queue]} {
  set net [lindex $queue 0]
  set queue [lrange $queue 1 end]
  if {!$first} { incr n_subnets }
  set first 0
  foreach it [$net getITerms] {
    if {![$it isInputSignal]} { continue }
    set inst [$it getInst]
    if {[string match DFF* [[$inst getMaster] getName]]} { incr n_sinks; continue }
    incr n_buf
    foreach ot [$inst getITerms] {
      if {[$ot isOutputSignal] && [$ot getNet] ne "NULL"} { lappend queue [$ot getNet] }
    }
  }
}
set f [open outputs/ct02_cts_summary.txt w]
puts $f "clock_roots 1"
puts $f "clock_buffers_inserted $n_buf"
puts $f "clock_subnets $n_subnets"
puts $f "clock_sinks $n_sinks"
close $f
