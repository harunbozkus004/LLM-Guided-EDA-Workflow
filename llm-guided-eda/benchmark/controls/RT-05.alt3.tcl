# Alternative: reference-flow order -- filler cells first, then detailed routing with ORFS options.
filler_placement FILLCELL*
detailed_route -output_drc outputs/route_drc.rpt -bottom_routing_layer metal2 -top_routing_layer metal10 \
  -save_guide_updates -clean_patches -droute_end_iter 64 -verbose 1
