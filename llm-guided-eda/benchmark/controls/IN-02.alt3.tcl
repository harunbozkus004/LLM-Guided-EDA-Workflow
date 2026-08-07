# Alternative: hand-written structural Verilog dumped from OpenDB. Nets are renamed n<k>, port bits are
# written as escaped scalar identifiers and bound to their nets with assign statements.
set block [ord::get_db_block]
set net_id [dict create]
set k 0
foreach net [$block getNets] {
  if {[$net getSigType] in {POWER GROUND}} { continue }
  dict set net_id [$net getName] "n[incr k]"
}
set fh [open outputs/gcd_netlist.v w]
set ports {}
foreach bterm [$block getBTerms] { lappend ports "\\[$bterm getName] " }
puts $fh "module gcd ([join $ports {, }]);"
foreach bterm [$block getBTerms] {
  puts $fh "  [string tolower [$bterm getIoType]] \\[$bterm getName] ;"
}
foreach id [dict values $net_id] { puts $fh "  wire $id;" }
foreach bterm [$block getBTerms] {
  set net [$bterm getNet]
  if {$net ne "NULL"} { puts $fh "  assign \\[$bterm getName]  = [dict get $net_id [$net getName]];" }
}
foreach inst [$block getInsts] {
  set master [$inst getMaster]
  if {[$master getType] ne "CORE"} { continue }
  set conns {}
  foreach iterm [$inst getITerms] {
    set net [$iterm getNet]
    if {$net eq "NULL" || [$net getSigType] in {POWER GROUND}} { continue }
    lappend conns ".[[$iterm getMTerm] getName]([dict get $net_id [$net getName]])"
  }
  puts $fh "  [$master getName] [$inst getName] ([join $conns {, }]);"
}
puts $fh "endmodule"
close $fh
