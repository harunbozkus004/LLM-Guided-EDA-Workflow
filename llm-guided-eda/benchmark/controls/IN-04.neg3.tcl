# Wrong: OpenDB terminal count without skipping the power/ground nets (VDD/VSS come out on top).
set block [ord::get_db_block]
set rows {}
foreach net [$block getNets] {
  if {[$net getName] eq "clk"} { continue }
  lappend rows [list [$net getName] [expr {[$net getITermCount] + [$net getBTermCount] - 1}]]
}
set fh [open outputs/high_fanout_nets.txt w]
foreach row [lrange [lsort -integer -decreasing -index 1 $rows] 0 4] { puts $fh [join $row " "] }
close $fh
