# Alternative: route, then write the DRC report with the router's DRC checker in the same session.
detailed_route -bottom_routing_layer metal2 -top_routing_layer metal10
drt::check_drc -output_file outputs/route_drc.rpt
