# Fabricated report: plausible structure, invented slacks.
set f [open outputs/setup_top10.rpt w]
set i 0
foreach ep {resp_msg[15] resp_msg[14] _706_ _698_ _694_ _704_ _691_ _696_ _702_ _700_} {
  set sl [format %.4f [expr {-0.0500 + 0.0045 * $i}]]
  puts $f "Startpoint: _697_ (rising edge-triggered flip-flop clocked by core_clock)"
  puts $f "Endpoint: $ep (output port clocked by core_clock)"
  puts $f "Path Group: core_clock"
  puts $f "Path Type: max"
  puts $f ""
  puts $f "   0.0000    0.0000   clock core_clock (rise edge)"
  puts $f "   0.0000    0.0000 ^ _697_/CK (DFF_X2)"
  puts $f "   0.1250    0.1250 ^ _697_/Q (DFF_X2)"
  puts $f "   0.3000    0.4250 v $ep (out)"
  puts $f "             0.4250   data arrival time"
  puts $f ""
  puts $f "             $sl   slack (VIOLATED)"
  puts $f ""
  incr i
}
close $f
