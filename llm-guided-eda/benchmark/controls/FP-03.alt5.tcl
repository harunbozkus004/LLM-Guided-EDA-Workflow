# Alternative: longer pins that extend beyond the die boundary (pin length / extension settings).
set_pin_length -hor_length 1.0 -ver_length 1.0
set_pin_length_extension -hor_extension 0.5 -ver_extension 0.5
place_pins -hor_layers metal5 -ver_layers metal4 -min_distance 4
