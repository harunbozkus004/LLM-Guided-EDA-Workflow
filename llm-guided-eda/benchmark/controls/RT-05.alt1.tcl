# Alternative: explicit pin access and routing layer range (as in the reference flow).
pin_access -bottom_routing_layer metal2 -top_routing_layer metal10
detailed_route -output_drc outputs/route_drc.rpt -no_pin_access \
  -bottom_routing_layer metal2 -top_routing_layer metal10 -verbose 0
