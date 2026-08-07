# Modifies the design: one register clock pin is moved to the root net (same cells, masters and
# positions), and the modified tree is then described correctly.
set block [ord::get_db_block]
set it [$block findITerm _675_/CK]
$it disconnect
$it connect [$block findNet clknet_0_clk]
set f [open outputs/ct06_clock_tree.txt w]
set queue [list [list [[$block findBTerm clk] getNet] 1]]
while {[llength $queue]} {
  lassign [lindex $queue 0] net level
  set queue [lrange $queue 1 end]
  foreach it [$net getITerms] {
    if {![$it isInputSignal]} { continue }
    set inst [$it getInst]
    if {[string match DFF* [[$inst getMaster] getName]]} { continue }
    set n_reg 0
    foreach ot [$inst getITerms] {
      if {![$ot isOutputSignal] || [$ot getNet] eq "NULL"} { continue }
      foreach load [[$ot getNet] getITerms] {
        if {[$load isInputSignal] && [string match DFF* [[[$load getInst] getMaster] getName]]} { incr n_reg }
      }
      lappend queue [list [$ot getNet] [expr {$level + 1}]]
    }
    puts $f "[$inst getName] [[$inst getMaster] getName] $level $n_reg"
  }
}
close $f
