# Alternative: coordinates from variables, default site, tracks created layer by layer.
set die {0.0 0.0 120.0 100.0}
set core [list 10.0 10.0 110.0 90.0]
initialize_floorplan -die_area $die -core_area $core
foreach layer [[ord::get_db_tech] getLayers] {
  if {[$layer getType] == "ROUTING"} { make_tracks [$layer getName] }
}
