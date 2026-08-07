# Wrong order: the top five are written in increasing fanout order.
set block [ord::get_db_block]
set rows {}
foreach net [$block getNets] {
  if {[$net getSigType] in {POWER GROUND CLOCK}} { continue }
  lappend rows [list [$net getName] [expr {[$net getITermCount] + [$net getBTermCount] - 1}]]
}
set fh [open outputs/high_fanout_nets.txt w]
foreach row [lrange [lsort -integer -increasing -index 1 $rows] end-4 end] { puts $fh [join $row " "] }
close $fh
