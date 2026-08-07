# Padding applied only during global placement; the legalizer runs without padding.
global_placement -pad_left 1 -pad_right 1
place_pins -hor_layers metal3 -ver_layers metal2
detailed_placement
