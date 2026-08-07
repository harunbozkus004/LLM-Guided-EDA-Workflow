# Alternative: STA view of nets, pins and ports.
set fh [open outputs/unloaded_nets.txt w]
foreach net [get_nets *] {
  set drivers [get_pins -quiet -of_objects $net -filter "direction==output"]
  set loads [llength [get_pins -quiet -of_objects $net -filter "direction==input"]]
  foreach port [get_ports -quiet -of_objects $net] {
    if {[get_property $port direction] eq "output"} { incr loads }
  }
  if {$loads == 0 && [llength $drivers] > 0} {
    puts $fh "[get_full_name $net] [get_full_name [lindex $drivers 0]]"
  }
}
close $fh
