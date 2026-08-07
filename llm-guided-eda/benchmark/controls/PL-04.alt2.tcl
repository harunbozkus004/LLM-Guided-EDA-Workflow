# Alternative: density 0.5 with a lower initial density penalty, then a padded legalization.
global_placement -density 0.5 -init_density_penalty 0.01
set_placement_padding -global -left 1 -right 1
detailed_placement
