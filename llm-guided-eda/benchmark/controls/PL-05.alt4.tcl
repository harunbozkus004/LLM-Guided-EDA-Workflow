# Alternative: padding on the logic (CORE) masters only; tap cells unpadded.
set masters {}
foreach lib [[ord::get_db] getLibs] { foreach m [$lib getMasters] { if {[$m getType] eq "CORE"} { lappend masters [$m getName] } } }
set_placement_padding -masters $masters -left 2 -right 2
detailed_placement
