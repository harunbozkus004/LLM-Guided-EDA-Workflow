# Alternative: ORFS-style two passes (IO pins ignored first, then a normal Nesterov pass), density 0.3.
global_placement -skip_io -density 0.3
global_placement -density 0.3 -skip_initial_place
