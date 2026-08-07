# Wrong: exports the DEF, then changes the design (removes the tap cells) although the task forbids changes.
write_def -version 5.7 outputs/gcd_floorplan.def
tapcell_ripup
