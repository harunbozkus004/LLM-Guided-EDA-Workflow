# Wrong: a generic grid in another platform's style (metal4 + metal5 straps) instead of the platform configuration.
add_global_connection -net VDD -pin_pattern {^VDD$} -power
add_global_connection -net VSS -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name grid -voltage_domains CORE
add_pdn_stripe -grid grid -layer metal1 -width 0.17 -followpins
add_pdn_stripe -grid grid -layer metal4 -width 0.48 -pitch 56.0 -offset 2
add_pdn_stripe -grid grid -layer metal5 -width 0.48 -pitch 40.0 -offset 2
add_pdn_connect -grid grid -layers {metal1 metal4}
add_pdn_connect -grid grid -layers {metal4 metal5}
pdngen
