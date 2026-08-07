# Describe the existing clock tree: one line per clock buffer with its cell,
# level below the clk port and the number of register clock pins it drives.
set block [ord::get_db_block]
set f [open outputs/ct06_clock_tree.txt w]
set queue [list [list [[$block findBTerm clk] getNet] 1]]
while {[llength $queue]} {
  lassign [lindex $queue 0] net level
  set queue [lrange $queue 1 end]
  foreach it [$net getITerms] {
    if {![$it isInputSignal]} { continue }
    set inst [$it getInst]
    set master [$inst getMaster]
    if {[string match DFF* [$master getName]]} { continue }
    # Count register clock pins on this buffer's output net.
    set n_reg 0
    foreach ot [$inst getITerms] {
      if {![$ot isOutputSignal] || [$ot getNet] eq "NULL"} { continue }
      foreach load [[$ot getNet] getITerms] {
        if {[$load isInputSignal] && [string match DFF* [[[$load getInst] getMaster] getName]]} { incr n_reg }
      }
      lappend queue [list [$ot getNet] [expr {$level + 1}]]
    }
    puts $f "[$inst getName] [$master getName] $level $n_reg"
  }
}
close $f
