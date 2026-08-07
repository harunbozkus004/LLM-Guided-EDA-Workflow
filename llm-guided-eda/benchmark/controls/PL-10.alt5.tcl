# Alternative: timing-driven placement at density 0.5, pins with a minimum spacing in tracks, master padding.
global_placement -density 0.5 -timing_driven
place_pins -hor_layers {metal3} -ver_layers {metal2} -min_distance 2 -min_distance_in_tracks
set_placement_padding -masters {*} -left 1 -right 1
detailed_placement
