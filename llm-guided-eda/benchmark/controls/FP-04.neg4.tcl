# Wrong: re-places the IO pins "to be safe" before exporting, so the DEF no longer matches the floorplan.
place_pins -hor_layers metal3 -ver_layers metal2
write_def -version 5.7 outputs/gcd_floorplan.def
