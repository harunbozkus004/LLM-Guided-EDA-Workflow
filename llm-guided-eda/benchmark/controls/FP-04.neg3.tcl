# Wrong: hand-written DEF skeleton (header and die area only) instead of exporting the design.
set f [open outputs/gcd_floorplan.def w]
puts $f "VERSION 5.7 ;"
puts $f "DIVIDERCHAR \"/\" ;"
puts $f "BUSBITCHARS \"\[\]\" ;"
puts $f "DESIGN gcd ;"
puts $f "UNITS DISTANCE MICRONS 2000 ;"
puts $f "DIEAREA ( 0 0 ) ( 200260 201600 ) ;"
puts $f "END DESIGN"
close $f
