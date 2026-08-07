# Alternative: ORFS-style -skip_io pass, IO pins re-placed, then a second pass at density 0.5.
global_placement -skip_io -density 0.5
place_pins -hor_layers metal3 -ver_layers metal2
global_placement -density 0.5 -skip_initial_place
