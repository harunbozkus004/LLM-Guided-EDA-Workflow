# Alternative: HPWL from instance-pin bounding-box centres; optimizer with another seed plus mirroring.
proc hpwl_um {} {
  set block [ord::get_db_block]
  set dbu [$block getDefUnits]
  set sum 0.0
  foreach net [$block getNets] {
    if {[$net isSpecial] || [$net getSigType] eq "POWER" || [$net getSigType] eq "GROUND"} continue
    set pts {}
    foreach it [$net getITerms] {
      set b [$it getBBox]
      lappend pts [list [expr {([$b xMin] + [$b xMax]) / 2.0}] [expr {([$b yMin] + [$b yMax]) / 2.0}]]
    }
    foreach bt [$net getBTerms] {
      set b [$bt getBBox]
      lappend pts [list [expr {([$b xMin] + [$b xMax]) / 2.0}] [expr {([$b yMin] + [$b yMax]) / 2.0}]]
    }
    if {[llength $pts] < 2} continue
    set xs [lsort -real -index 0 $pts]
    set ys [lsort -real -index 1 $pts]
    set sum [expr {$sum + [lindex $xs end 0] - [lindex $xs 0 0] + [lindex $ys end 1] - [lindex $ys 0 1]}]
  }
  return [expr {$sum / $dbu}]
}
set h0 [hpwl_um]
improve_placement -random_seed 7
optimize_mirroring
check_placement
set h1 [hpwl_um]
puts "HPWL $h0 -> $h1"
set fh [open outputs/hpwl.txt w]
puts $fh "hpwl_before_um: [format %.2f $h0]"
puts $fh "hpwl_after_um: [format %.2f $h1]"
close $fh
