# Alternative: OpenDB terminal counts (every net has one driver, so sinks = terminals - 1);
# supply and clock nets skipped by signal type.
set block [ord::get_db_block]
set rows {}
foreach net [$block getNets] {
  if {[$net getSigType] in {POWER GROUND CLOCK}} { continue }
  lappend rows [list [$net getName] [expr {[$net getITermCount] + [$net getBTermCount] - 1}]]
}
set fh [open outputs/high_fanout_nets.txt w]
foreach row [lrange [lsort -integer -decreasing -index 1 $rows] 0 4] { puts $fh [format "%-10s %4d" {*}$row] }
close $fh
