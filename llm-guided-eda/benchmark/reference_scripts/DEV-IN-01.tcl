# Nets with a driver but no sink (no cell input pin, no output port).
set block [ord::get_db_block]
set fh [open outputs/unloaded_nets.txt w]
foreach net [$block getNets] {
  if {[$net getSigType] in {POWER GROUND}} { continue }
  set drivers {}
  set loads 0
  foreach iterm [$net getITerms] {
    switch [$iterm getIoType] {
      OUTPUT { lappend drivers "[[$iterm getInst] getName]/[[$iterm getMTerm] getName]" }
      INPUT { incr loads }
    }
  }
  foreach bterm [$net getBTerms] {
    switch [$bterm getIoType] {
      INPUT { lappend drivers [$bterm getName] }
      OUTPUT { incr loads }
    }
  }
  if {$loads == 0 && [llength $drivers] > 0} { puts $fh "[$net getName] [lindex $drivers 0]" }
}
close $fh
