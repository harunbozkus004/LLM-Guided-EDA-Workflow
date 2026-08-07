# Padding set, then global placement re-run before legalizing: cells leave their global-placement locations.
set_placement_padding -global -left 2 -right 2
global_placement
detailed_placement
