# Alternative: start from instance output pins in OpenDB and check the other terminals of their nets.
set block [ord::get_db_block]
set fh [open outputs/unloaded_nets.txt w]
foreach inst [$block getInsts] {
  foreach iterm [$inst getITerms] {
    set net [$iterm getNet]
    if {$net eq "NULL" || ![$iterm isOutputSignal]} { continue }
    set loads [llength [lsearch -all -inline [lmap it [$net getITerms] {$it isInputSignal}] 1]]
    foreach bterm [$net getBTerms] { if {[$bterm getIoType] eq "OUTPUT"} { incr loads } }
    if {$loads == 0} { puts $fh [list [$net getName] "[$inst getName]/[[$iterm getMTerm] getName]"] }
  }
}
close $fh
