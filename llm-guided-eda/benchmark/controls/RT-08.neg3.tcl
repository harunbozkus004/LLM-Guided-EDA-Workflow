# Mistake: a hand-written DEF skeleton instead of the real layout.
set fh [open outputs/gcd_route.def w]
puts $fh "VERSION 5.8 ;"
puts $fh "DESIGN gcd ;"
puts $fh "UNITS DISTANCE MICRONS 2000 ;"
puts $fh "DIEAREA ( 0 0 ) ( 200260 201600 ) ;"
puts $fh "COMPONENTS 1877 ;"
puts $fh "END COMPONENTS"
puts $fh "PINS 54 ;"
puts $fh "END PINS"
puts $fh "NETS 447 ;"
puts $fh "END NETS"
puts $fh "END DESIGN"
close $fh
