# Wrong denominator: die area instead of core area (5.19 % instead of 8.18 %).
set block [ord::get_db_block]
set die [$block getDieArea]
set a [expr {double([$die dx]) * [$die dy]}]
set c 0.0
foreach inst [$block getInsts] { set m [$inst getMaster]; set c [expr {$c + double([$m getWidth]) * [$m getHeight]}] }
set u [expr {100.0 * $c / $a}]
set f [open outputs/utilization.txt w]
puts $f [format "utilization_percent: %.2f" $u]
puts $f "above_target: no"
close $f
