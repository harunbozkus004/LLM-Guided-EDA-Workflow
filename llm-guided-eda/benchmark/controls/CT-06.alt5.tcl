# Alternative: recursive depth-first walk through the database API, rows sorted by name and
# written as padded columns.
set regck {}
foreach p [all_registers -clock_pins] { dict set regck [get_full_name $p] 1 }
set rows {}
proc walk {net level} {
  global rows regck
  foreach it [$net getITerms] {
    if {![$it isInputSignal]} continue
    set inst [$it getInst]
    set pin "[$inst getName]/[[$it getMTerm] getName]"
    if {[dict exists $regck $pin]} continue
    set out [$inst getFirstOutput]
    set onet [$out getNet]
    set n 0
    foreach l [$onet getITerms] {
      if {[$l isInputSignal] && [dict exists $regck "[[$l getInst] getName]/[[$l getMTerm] getName]"]} { incr n }
    }
    lappend rows [list [$inst getName] [[$inst getMaster] getName] $level $n]
    walk $onet [expr {$level + 1}]
  }
}
walk [[[ord::get_db_block] findBTerm clk] getNet] 1
set f [open outputs/ct06_clock_tree.txt w]
foreach r [lsort -index 0 $rows] { puts $f [format "%-22s %-8s %3d %4d" {*}$r] }
close $f
