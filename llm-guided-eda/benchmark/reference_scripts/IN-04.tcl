# Fanout = input pins of cell instances + top-level output ports on the net.
set block [ord::get_db_block]
set clock_net [[$block findBTerm clk] getNet]
set rows {}
foreach net [$block getNets] {
  if {[$net getSigType] in {POWER GROUND} || [$net getName] eq [$clock_net getName]} { continue }
  set fanout 0
  foreach iterm [$net getITerms] {
    if {[$iterm getIoType] eq "INPUT"} { incr fanout }
  }
  foreach bterm [$net getBTerms] {
    if {[$bterm getIoType] eq "OUTPUT"} { incr fanout }
  }
  lappend rows [list [$net getName] $fanout]
}
set fh [open outputs/high_fanout_nets.txt w]
foreach row [lrange [lsort -integer -decreasing -index 1 $rows] 0 4] {
  puts $fh "[lindex $row 0] [lindex $row 1]"
}
close $fh
