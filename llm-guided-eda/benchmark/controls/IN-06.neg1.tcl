# Wrong detection: dbMaster isSequential is false for every master in this build, so nothing is found.
set block [ord::get_db_block]
set types [dict create]
set drivers [dict create]
foreach inst [$block getInsts] {
  set master [$inst getMaster]
  if {![$master isSequential]} { continue }
  dict incr types [$master getName]
  set net [[$inst findITerm CK] getNet]
  foreach iterm [$net getITerms] {
    if {[$iterm getIoType] eq "OUTPUT"} { dict incr drivers [[$iterm getInst] getName] }
  }
}
set total 0
set fh [open outputs/flop_types.txt w]
dict for {ref n} $types { puts $fh "$ref $n"; incr total $n }
puts $fh "total $total"
close $fh
set fh [open outputs/flop_clock_drivers.txt w]
dict for {inst n} $drivers { puts $fh "$inst $n" }
close $fh
