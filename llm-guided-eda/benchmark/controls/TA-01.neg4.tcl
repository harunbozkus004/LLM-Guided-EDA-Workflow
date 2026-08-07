# Fabricated report written with puts (plausible format, invented numbers).
set f [open outputs/hold_paths.rpt w]
foreach {ep sl} {_674_ 0.0612 _672_ 0.0634 _693_ 0.0671} {
  puts $f "Startpoint: _690_ (rising edge-triggered flip-flop clocked by core_clock)"
  puts $f "Endpoint: $ep (rising edge-triggered flip-flop clocked by core_clock)"
  puts $f "Path Group: core_clock"
  puts $f "Path Type: min"
  puts $f ""
  puts $f "   0.0000    0.0000   clock core_clock (rise edge)"
  puts $f "   0.0450    0.0450 ^ _690_/CK (DFF_X1)"
  puts $f "   0.0800    0.1250 v _690_/Q (DFF_X1)"
  puts $f "   0.0000    0.1250 v $ep/D (DFF_X2)"
  puts $f "             0.1250   data arrival time"
  puts $f ""
  puts $f "             $sl   slack (MET)"
  puts $f ""
}
close $f
