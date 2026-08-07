# Partial: the driving instance is written without its pin.
set fh [open outputs/unloaded_nets.txt w]
foreach net [get_nets *] {
  set drivers [get_pins -quiet -of_objects $net -filter "direction==output"]
  set loads [llength [get_pins -quiet -of_objects $net -filter "direction==input"]]
  if {$loads == 0 && [llength [get_ports -quiet -of_objects $net]] == 0 && [llength $drivers]} {
    puts $fh "[get_full_name $net] [get_full_name [get_cells -of_objects [lindex $drivers 0]]]"
  }
}
close $fh
