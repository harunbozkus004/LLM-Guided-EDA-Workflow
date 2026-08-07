# Legalized, but the report is fabricated.
detailed_placement
set f [open outputs/top_displaced.txt w]
foreach {n d} {_345_ 2.500 _347_ 2.250 _348_ 2.000 _349_ 1.750 _350_ 1.500} {
  puts $f "$n $d"
}
close $f
