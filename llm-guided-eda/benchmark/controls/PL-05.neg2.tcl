# Padding applied only during (incremental) global placement; the legalizer runs without padding.
global_placement -incremental -pad_left 2 -pad_right 2
detailed_placement
