# Confuses floating nets (loads but no driver) with unloaded nets: finds nothing.
set fh [open outputs/unloaded_nets.txt w]
foreach net [get_nets *] {
  set drivers [get_pins -quiet -of_objects $net -filter "direction==output"]
  set loads [get_pins -quiet -of_objects $net -filter "direction==input"]
  if {[llength $drivers] == 0 && [llength $loads] > 0 && [llength [get_ports -quiet -of_objects $net]] == 0} {
    puts $fh "[get_full_name $net] none"
  }
}
close $fh
