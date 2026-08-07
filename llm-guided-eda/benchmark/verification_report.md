# Benchmark verification report

649/649 controls behaved as expected across 58 tasks.

| Task | Control | Expected | Got | Detail |
|---|---|---|---|---|
| CT-01 | reference | PASS | PASS | PASS (5 checks) |
| CT-01 | empty | FAIL | FAIL | FAIL - clock_tree_built: 35/35 register clock pins reached from the clock port, 35 driven directly by the port, 0 clock- |
| CT-01 | alt1 | PASS | PASS | PASS (5 checks) |
| CT-01 | alt2 | PASS | PASS | PASS (5 checks) |
| CT-01 | alt3 | PASS | PASS | PASS (5 checks) |
| CT-01 | alt4 | PASS | PASS | PASS (5 checks) |
| CT-01 | alt5 | PASS | PASS | PASS (5 checks) |
| CT-01 | neg1 | FAIL | FAIL | FAIL - clock_buffer_masters: root ['CLKBUF_X3'], tree ['CLKBUF_X3'] (expected root ['BUF_X4'], tree ['BUF_X4']); masters |
| CT-01 | neg2 | FAIL | FAIL | FAIL - clock_buffer_masters: root ['BUF_X2'], tree ['BUF_X2'] (expected root ['BUF_X4'], tree ['BUF_X4']); masters used  |
| CT-01 | neg3 | FAIL | FAIL | FAIL - clock_tree_built: 35/35 register clock pins reached from the clock port, 35 driven directly by the port, 0 clock- |
| CT-01 | neg4 | FAIL | FAIL | FAIL - clock_tree_built: 35/35 register clock pins reached from the clock port, 35 driven directly by the port, 0 clock- |
| CT-01 | neg5 | FAIL | FAIL | FAIL - script_completed: tool_error: [ERROR CTS-0055] Missing argument -buf_list; clock_tree_built: 35/35 register clock |
| CT-02 | reference | PASS | PASS | PASS (9 checks) |
| CT-02 | empty | FAIL | FAIL | FAIL - clock_tree_built: 35/35 register clock pins reached from the clock port, 35 driven directly by the port, 0 clock- |
| CT-02 | alt1 | PASS | PASS | PASS (9 checks) |
| CT-02 | alt2 | PASS | PASS | PASS (9 checks) |
| CT-02 | alt3 | PASS | PASS | PASS (9 checks) |
| CT-02 | alt4 | PASS | PASS | PASS (9 checks) |
| CT-02 | neg1 | FAIL | FAIL | FAIL - summary_roots: reported 0, actual 1; summary_buffers: reported 0, actual 5; summary_subnets: reported 0, actual 5 |
| CT-02 | neg2 | FAIL | FAIL | FAIL - script_completed: invalid_argument: [ERROR STA-0406] report_cts positional arguments not supported.; summary_repo |
| CT-02 | neg3 | FAIL | FAIL | FAIL - summary_buffers: reported 4, actual 5; summary_subnets: reported 4, actual 5 |
| CT-02 | neg4 | FAIL | FAIL | FAIL - clock_buffer_masters: root ['BUF_X4'], tree ['BUF_X4'] (expected root ['BUF_X8'], tree ['BUF_X8']); masters used  |
| CT-02 | neg5 | FAIL | FAIL | FAIL - summary_roots: reported nothing, actual 1; summary_buffers: reported nothing, actual 5; summary_subnets: reported |
| CT-02 | neg6 | FAIL | FAIL | FAIL - summary_report: outputs/ct02_cts_summary.txt missing |
| CT-02 | neg7 | FAIL | FAIL | FAIL - summary_subnets: reported 6, actual 5 |
| CT-03 | reference | PASS | PASS | PASS (4 checks) |
| CT-03 | empty | FAIL | FAIL | FAIL - skew_report: outputs/ct03_clock_skew.rpt missing |
| CT-03 | alt1 | PASS | PASS | PASS (4 checks) |
| CT-03 | alt2 | PASS | PASS | PASS (4 checks) |
| CT-03 | alt3 | PASS | PASS | PASS (4 checks) |
| CT-03 | alt4 | PASS | PASS | PASS (4 checks) |
| CT-03 | alt5 | PASS | PASS | PASS (4 checks) |
| CT-03 | alt6 | PASS | PASS | PASS (4 checks) |
| CT-03 | neg1 | FAIL | FAIL | FAIL - skew_value: reported 0.0018, actual 0.003232 ns (tol 0.0001); skew_pins: worst-skew register clock pins ['_675_/C |
| CT-03 | neg2 | FAIL | FAIL | FAIL - skew_value: reported 0.0, actual 0.003232 ns (tol 0.0001) |
| CT-03 | neg3 | FAIL | FAIL | FAIL - skew_value: reported 0.005, actual 0.003232 ns (tol 0.0001); skew_pins: worst-skew register clock pins ['_675_/CK |
| CT-03 | neg4 | FAIL | FAIL | FAIL - skew_value: reported -0.0975, actual 0.003232 ns (tol 0.0001); skew_pins: worst-skew register clock pins ['_675_/ |
| CT-03 | neg5 | FAIL | FAIL | FAIL - design_unchanged: insts 466/466, moved cells 0, masters changed, placement status same, clock tree changed |
| CT-03 | neg6 | FAIL | FAIL | FAIL - skew_pins: worst-skew register clock pins ['_675_/CK', '_679_/CK'] |
| CT-03 | neg7 | FAIL | FAIL | FAIL - design_unchanged: insts 466/466, moved cells 0, masters changed, placement status same, clock tree same |
| CT-04 | reference | PASS | PASS | PASS (7 checks) |
| CT-04 | empty | FAIL | FAIL | FAIL - clock_tree_built: 35/35 register clock pins reached from the clock port, 35 driven directly by the port, 0 clock- |
| CT-04 | alt1 | PASS | PASS | PASS (7 checks) |
| CT-04 | alt2 | PASS | PASS | PASS (7 checks) |
| CT-04 | alt3 | PASS | PASS | PASS (7 checks) |
| CT-04 | alt4 | PASS | PASS | PASS (7 checks) |
| CT-04 | alt5 | PASS | PASS | PASS (7 checks) |
| CT-04 | neg1 | FAIL | FAIL | FAIL - clock_buffer_masters: root ['BUF_X8'], tree ['BUF_X8'] (expected root ['BUF_X8'], tree ['BUF_X2']); masters used  |
| CT-04 | neg2 | FAIL | FAIL | FAIL - placement_legal: check_placement legal=False |
| CT-04 | neg3 | FAIL | FAIL | FAIL - clock_buffer_masters: root ['BUF_X2'], tree ['BUF_X2', 'BUF_X8'] (expected root ['BUF_X8'], tree ['BUF_X2']); mas |
| CT-04 | neg4 | FAIL | FAIL | FAIL - placement_legal: check_placement legal=False |
| CT-04 | neg5 | FAIL | FAIL | FAIL - clock_buffer_masters: root ['BUF_X8'], tree ['BUF_X8'] (expected root ['BUF_X8'], tree ['BUF_X2']); masters used  |
| CT-04 | neg6 | FAIL | FAIL | FAIL - clock_buffer_masters: root ['BUF_X8'], tree ['BUF_X8'] (expected root ['BUF_X8'], tree ['BUF_X2']); masters used  |
| CT-05 | reference | PASS | PASS | PASS (9 checks) |
| CT-05 | empty | FAIL | FAIL | FAIL - clock_tree_built: 35/35 register clock pins reached from the clock port, 35 driven directly by the port, 0 clock- |
| CT-05 | alt1 | PASS | PASS | PASS (9 checks) |
| CT-05 | alt2 | PASS | PASS | PASS (9 checks) |
| CT-05 | alt3 | PASS | PASS | PASS (9 checks) |
| CT-05 | alt4 | PASS | PASS | PASS (9 checks) |
| CT-05 | neg1 | FAIL | FAIL | FAIL - metric_clock_skew: reported 0.0018, actual 0.003232 ns (tol 0.0001) |
| CT-05 | neg2 | FAIL | FAIL | FAIL - placement_legal: check_placement legal=False |
| CT-05 | neg3 | FAIL | FAIL | FAIL - clock_tree_built: 35/35 register clock pins reached from the clock port, 35 driven directly by the port, 0 clock- |
| CT-05 | neg4 | FAIL | FAIL | FAIL - metric_clock_skew: reported 0.0000, actual 0.003232 ns (tol 0.0001) |
| CT-05 | neg5 | FAIL | FAIL | FAIL - metric_clock_buffers: reported 4, actual 5 |
| CT-05 | neg6 | FAIL | FAIL | FAIL - metric_clock_skew: reported 0.0018, actual 0.003232 ns (tol 0.0001) |
| CT-05 | neg7 | FAIL | FAIL | FAIL - metric_clock_skew: reported 0.001823, actual 0.003232 ns (tol 0.0001) |
| CT-05 | neg8 | FAIL | FAIL | FAIL - metric_clock_skew: reported 0.00, actual 0.003232 ns (tol 0.0001) |
| CT-05 | neg9 | FAIL | FAIL | FAIL - placement_legal: check_placement legal=False |
| CT-06 | reference | PASS | PASS | PASS (5 checks) |
| CT-06 | empty | FAIL | FAIL | FAIL - tree_report: outputs/ct06_clock_tree.txt missing |
| CT-06 | alt1 | PASS | PASS | PASS (5 checks) |
| CT-06 | alt2 | PASS | PASS | PASS (5 checks) |
| CT-06 | alt3 | PASS | PASS | PASS (5 checks) |
| CT-06 | alt4 | PASS | PASS | PASS (5 checks) |
| CT-06 | alt5 | PASS | PASS | PASS (5 checks) |
| CT-06 | neg1 | FAIL | FAIL | FAIL - buffer_attributes: cell/level/register sinks wrong for 5: ["clkbuf_0_clk: ('BUF_X4', 1, 5) vs ('BUF_X4', 1, 0)",  |
| CT-06 | neg2 | FAIL | FAIL | FAIL - buffer_attributes: cell/level/register sinks wrong for 5: ["clkbuf_0_clk: ('BUF_X4', 0, 0) vs ('BUF_X4', 1, 0)",  |
| CT-06 | neg3 | FAIL | FAIL | FAIL - buffer_attributes: cell/level/register sinks wrong for 3: ["clkbuf_2_0__f_clk: ('BUF_X4', 2, 9) vs ('BUF_X4', 2,  |
| CT-06 | neg4 | FAIL | FAIL | FAIL - buffer_attributes: cell/level/register sinks wrong for 1: ["clkbuf_0_clk: ('BUF_X4', 1, 4) vs ('BUF_X4', 1, 0)"] |
| CT-06 | neg5 | FAIL | FAIL | FAIL - report_format: 5 buffer lines, malformed ['instance cell level register_sinks'] |
| CT-06 | neg6 | FAIL | FAIL | FAIL - design_unchanged: insts 466/466, moved cells 0, masters same, placement status same, clock tree changed |
| CT-06 | neg7 | FAIL | FAIL | FAIL - buffer_attributes: cell/level/register sinks wrong for 1: ["clkbuf_0_clk: ('BUF_X4', 1, 35) vs ('BUF_X4', 1, 0)"] |
| CT-06 | neg8 | FAIL | FAIL | FAIL - buffer_set: 5 clock buffers; missing ['clkbuf_0_clk'], not in the clock tree [] |
| FP-01 | reference | PASS | PASS | PASS (10 checks) |
| FP-01 | empty | FAIL | FAIL | FAIL - rows_created: 0 rows of site ''; core_utilization: value unavailable (target 0.4); die_and_core_defined: die or c |
| FP-01 | alt1 | PASS | PASS | PASS (10 checks) |
| FP-01 | alt2 | PASS | PASS | PASS (10 checks) |
| FP-01 | alt3 | PASS | PASS | PASS (10 checks) |
| FP-01 | neg1 | FAIL | FAIL | FAIL - core_utilization: value 0.00402574, target 0.4 +/- 0.02 |
| FP-01 | neg2 | FAIL | FAIL | FAIL - report_core: reported [2.0, 2.0, 38.045, 38.045], database [2.09, 2.8, 38.0, 37.8] (+/- 0.01 um); report_util: va |
| FP-01 | neg3 | FAIL | FAIL | FAIL - core_to_die_margins: margins L/B/R/T 0.000, 0.000, 0.135, 1.045 (allowed L/R 1.95..2.2, B/T 1.95..3.45) |
| FP-01 | neg4 | FAIL | FAIL | FAIL - report_util: value 0.4135, target 41.3545 +/- 0.55 |
| FP-01 | neg5 | FAIL | FAIL | FAIL - report_util: value 32.412, target 41.3545 +/- 0.55 |
| FP-01 | neg6 | FAIL | FAIL | FAIL - report_core: reported [2.0, 2.0, 38.045, 38.045], database [2.09, 2.8, 38.0, 37.8] (+/- 0.01 um) |
| FP-01 | neg7 | FAIL | FAIL | FAIL - report_util: value 28.802, target 41.3545 +/- 0.55 |
| FP-02 | reference | PASS | PASS | PASS (6 checks) |
| FP-02 | empty | FAIL | FAIL | FAIL - rows_created: 0 rows of site ''; die_and_core_defined: die or core area missing; routing_tracks_all_layers: missi |
| FP-02 | alt1 | PASS | PASS | PASS (6 checks) |
| FP-02 | alt2 | PASS | PASS | PASS (6 checks) |
| FP-02 | alt3 | PASS | PASS | PASS (6 checks) |
| FP-02 | neg1 | FAIL | FAIL | FAIL - core_area: core (row bbox) [10.07, 11.2, 99.94, 79.8], requested [10, 10, 110, 90]; edges may snap inwards by < 1 |
| FP-02 | neg2 | FAIL | FAIL | FAIL - routing_tracks_all_layers: missing track grids: ['metal1', 'metal2', 'metal3', 'metal4', 'metal5', 'metal6', 'met |
| FP-02 | neg3 | FAIL | FAIL | FAIL - die_area: die [0.0, 0.0, 100.0, 120.0], requested [0, 0, 120, 100]; core_area: core (row bbox) [10.07, 11.2, 89.8 |
| FP-02 | neg4 | FAIL | FAIL | FAIL - routing_tracks_all_layers: missing track grids: ['metal1', 'metal2', 'metal3', 'metal4', 'metal5', 'metal6', 'met |
| FP-02 | neg5 | FAIL | FAIL | FAIL - routing_tracks_all_layers: missing track grids: ['metal1', 'metal7', 'metal8', 'metal9', 'metal10'] |
| FP-03 | reference | PASS | PASS | PASS (7 checks) |
| FP-03 | empty | FAIL | FAIL | FAIL - all_pins_placed: 0/54 placed; unplaced e.g. ['clk', 'req_msg[0]', 'req_msg[10]', 'req_msg[11]']; pins_on_die_boun |
| FP-03 | alt1 | PASS | PASS | PASS (7 checks) |
| FP-03 | alt2 | PASS | PASS | PASS (7 checks) |
| FP-03 | alt3 | PASS | PASS | PASS (7 checks) |
| FP-03 | alt4 | PASS | PASS | PASS (7 checks) |
| FP-03 | alt5 | PASS | PASS | PASS (7 checks) |
| FP-03 | neg1 | FAIL | FAIL | FAIL - pin_layers: 54 pins on the wrong layer for their edge (expect metal5 left/right, metal4 top/bottom) ['clk:metal2@ |
| FP-03 | neg2 | FAIL | FAIL | FAIL - min_pin_spacing: closest neighbouring pins 0.56 um apart (left edge); required >= 4.0 um |
| FP-03 | neg3 | FAIL | FAIL | FAIL - min_pin_spacing: closest neighbouring pins 1.12 um apart (left edge); required >= 4.0 um |
| FP-03 | neg4 | FAIL | FAIL | FAIL - script_completed: tool_error: [ERROR PPL-0045] Layer metal4 preferred direction is not horizontal.; all_pins_plac |
| FP-03 | neg5 | FAIL | FAIL | FAIL - floorplan_unchanged: die [0.0, 0.0, 61.625, 61.625], core [10.07, 11.2, 51.49, 50.4], rows 28 |
| FP-04 | reference | PASS | PASS | PASS (12 checks) |
| FP-04 | empty | FAIL | FAIL | FAIL - def_file: outputs/gcd_floorplan.def missing or empty |
| FP-04 | alt1 | PASS | PASS | PASS (12 checks) |
| FP-04 | alt2 | PASS | PASS | PASS (12 checks) |
| FP-04 | neg1 | FAIL | FAIL | FAIL - def_version: VERSION 5.8, required 5.7 |
| FP-04 | neg2 | FAIL | FAIL | FAIL - def_version: VERSION None, required 5.7; def_design_units: DESIGN None, UNITS None; def_diearea: DIEAREA None, fl |
| FP-04 | neg3 | FAIL | FAIL | FAIL - def_rows: 0 ROW statements, floorplan 57; def_tracks: TRACKS on 0 layers, floorplan 10; def_components: 0 compone |
| FP-04 | neg4 | FAIL | FAIL | FAIL - design_unchanged: changed: ['io_pins']; def_pins: 54 pins (header 54); 54 missing/unplaced/moved vs the floorplan |
| FP-04 | neg5 | FAIL | FAIL | FAIL - def_file: outputs/gcd_floorplan.def missing or empty |
| FP-04 | neg6 | FAIL | FAIL | FAIL - design_unchanged: changed: ['inst_count', 'master_counts', 'status_counts'] |
| FP-05 | reference | PASS | PASS | PASS (8 checks) |
| FP-05 | empty | FAIL | FAIL | FAIL - all_pins_placed: 0/54 placed; unplaced e.g. ['clk', 'req_msg[0]', 'req_msg[10]', 'req_msg[11]']; pins_on_die_boun |
| FP-05 | alt1 | PASS | PASS | PASS (8 checks) |
| FP-05 | alt2 | PASS | PASS | PASS (8 checks) |
| FP-05 | alt3 | PASS | PASS | PASS (8 checks) |
| FP-05 | alt4 | PASS | PASS | PASS (8 checks) |
| FP-05 | neg1 | FAIL | FAIL | FAIL - bus_bit_order: 17 bits not after their predecessor along the edge, first at bit 3 |
| FP-05 | neg2 | FAIL | FAIL | FAIL - bus_bit_order: 31 bits not after their predecessor along the edge, first at bit 1 |
| FP-05 | neg3 | FAIL | FAIL | FAIL - bus_on_edge: 0/32 req_msg bits on the bottom edge; elsewhere: bits [0, 1, 2, 3, 4, 5] |
| FP-05 | neg4 | FAIL | FAIL | FAIL - bus_bit_order: 16 bits not after their predecessor along the edge, first at bit 2 |
| FP-05 | neg5 | FAIL | FAIL | FAIL - bus_bit_order: 1 bits not after their predecessor along the edge, first at bit 10 |
| FP-05 | neg6 | FAIL | FAIL | FAIL - bus_bit_order: 17 bits not after their predecessor along the edge, first at bit 3 |
| FP-06 | reference | PASS | PASS | PASS (10 checks) |
| FP-06 | empty | FAIL | FAIL | FAIL - taps_inserted: 0 TAPCELL_X1 cells, 0 not aligned to a row; endcaps_both_row_ends: 57/57 rows lack an endcap at th |
| FP-06 | alt1 | PASS | PASS | PASS (10 checks) |
| FP-06 | alt2 | PASS | PASS | PASS (10 checks) |
| FP-06 | alt3 | PASS | PASS | PASS (10 checks) |
| FP-06 | neg1 | FAIL | FAIL | FAIL - tap_row_pitch: 57 rows with taps closer than the checkerboard pitch (40 um; 20 um in the first/last row), e.g. ro |
| FP-06 | neg2 | FAIL | FAIL | FAIL - tap_coverage: largest gap between neighbouring taps in a row 79.99 um (row 1); allowed 40.40 um; checkerboard_sta |
| FP-06 | neg3 | FAIL | FAIL | FAIL - endcaps_both_row_ends: 57/57 rows lack an endcap at the start or end (e.g. rows [0, 1, 2, 3, 4]) |
| FP-06 | neg4 | FAIL | FAIL | FAIL - taps_do_not_overlap: 4 overlapping tap/endcap pairs; tap_row_pitch: 2 rows with taps closer than the checkerboard |
| FP-06 | neg5 | FAIL | FAIL | FAIL - checkerboard_stagger: 54/54 adjacent row pairs whose taps are not staggered by >= 20 um, e.g. rows 1/2 offset 0.0 |
| FP-07 | reference | PASS | PASS | PASS (10 checks) |
| FP-07 | empty | FAIL | FAIL | FAIL - supply_net_VDD: missing; supply_net_VSS: missing; grid_matches_config: 0/63 shapes of the configured grid present |
| FP-07 | alt1 | PASS | PASS | PASS (10 checks) |
| FP-07 | alt2 | PASS | PASS | PASS (10 checks) |
| FP-07 | alt3 | PASS | PASS | PASS (10 checks) |
| FP-07 | alt4 | PASS | PASS | PASS (10 checks) |
| FP-07 | neg1 | FAIL | FAIL | FAIL - grid_matches_config: 0/63 shapes of the configured grid present; missing {'VDD/metal4': 1, 'VDD/metal1': 29, 'VSS |
| FP-07 | neg2 | FAIL | FAIL | FAIL - grid_matches_config: 61/63 shapes of the configured grid present; missing {'VSS/metal7': 2}; grid_no_unconfigured |
| FP-07 | neg3 | FAIL | FAIL | FAIL - grid_matches_config: 62/63 shapes of the configured grid present; missing {'VDD/metal4': 1}; grid_no_unconfigured |
| FP-07 | neg4 | FAIL | FAIL | FAIL - grid_matches_config: 58/63 shapes of the configured grid present; missing {'VDD/metal4': 1, 'VSS/metal7': 2, 'VSS |
| FP-07 | neg5 | FAIL | FAIL | FAIL - grid_no_unconfigured_shapes: 3 supply shapes that the configured grid does not contain, e.g. ['VDD/metal4@(53.83, |
| FP-07 | neg6 | FAIL | FAIL | FAIL - grid_matches_config: 58/63 shapes of the configured grid present; missing {'VDD/metal4': 1, 'VSS/metal7': 2, 'VSS |
| FP-08 | reference | PASS | PASS | PASS (24 checks) |
| FP-08 | empty | FAIL | FAIL | FAIL - rows_created: 0 rows of site ''; core_utilization: value unavailable (target 0.3); die_and_core_defined: die or c |
| FP-08 | alt1 | PASS | PASS | PASS (24 checks) |
| FP-08 | alt2 | PASS | PASS | PASS (24 checks) |
| FP-08 | alt3 | PASS | PASS | PASS (24 checks) |
| FP-08 | neg1 | FAIL | FAIL | FAIL - pg_pins_connected: 362/451 instances with VDD->VDD and VSS->VSS; unconnected e.g. PHY_EDGE_ROW_0_Right_0 PHY_EDGE |
| FP-08 | neg2 | FAIL | FAIL | FAIL - script_completed: incorrect_design_context: [ERROR PPL-0021] Horizontal routing tracks not found for layer metal3 |
| FP-08 | neg3 | FAIL | FAIL | FAIL - grid_matches_config: 0/32 shapes of the configured grid present; missing {'VDD/metal4': 1, 'VDD/metal1': 15, 'VSS |
| FP-08 | neg4 | FAIL | FAIL | FAIL - core_utilization: value 0.00300554, target 0.3 +/- 0.02 |
| FP-08 | neg5 | FAIL | FAIL | FAIL - tap_coverage: largest gap between neighbouring taps in a row 41.23 um (row 1); allowed 30.40 um; checkerboard_sta |
| FP-08 | neg6 | FAIL | FAIL | FAIL - pin_layers: 54 pins on the wrong layer for their edge (expect metal3 left/right, metal2 top/bottom) ['clk:metal4@ |
| IN-01 | reference | PASS | PASS | PASS (6 checks) |
| IN-01 | empty | FAIL | FAIL | FAIL - file:outputs/io_ports.txt: missing |
| IN-01 | alt1 | PASS | PASS | PASS (6 checks) |
| IN-01 | alt2 | PASS | PASS | PASS (6 checks) |
| IN-01 | alt3 | PASS | PASS | PASS (6 checks) |
| IN-01 | neg1 | FAIL | FAIL | FAIL - port_set: 53 ports listed, 54 in design; missing ['clk'], unexpected [] |
| IN-01 | neg2 | FAIL | FAIL | FAIL - report_format: 54 unparseable line(s), e.g. 'clk SIGNAL'; port_set: 0 ports listed, 54 in design; missing ['clk', |
| IN-01 | neg3 | FAIL | FAIL | FAIL - port_set: 8 ports listed, 54 in design; missing ['req_msg[0]', 'req_msg[10]', 'req_msg[11]', 'req_msg[12]', 'req_ |
| IN-01 | neg4 | FAIL | FAIL | FAIL - file:outputs/io_ports.txt: missing |
| IN-02 | reference | PASS | PASS | PASS (7 checks) |
| IN-02 | empty | FAIL | FAIL | FAIL - file:outputs/gcd_netlist.v: missing |
| IN-02 | alt1 | PASS | PASS | PASS (7 checks) |
| IN-02 | alt2 | PASS | PASS | PASS (7 checks) |
| IN-02 | alt3 | PASS | PASS | PASS (7 checks) |
| IN-02 | alt4 | PASS | PASS | PASS (7 checks) |
| IN-02 | alt5 | PASS | PASS | PASS (7 checks) |
| IN-02 | neg1 | FAIL | FAIL | FAIL - instances: 352 standard cells in design; missing 5 ['clkbuf_0_clk', 'clkbuf_2_0__f_clk', 'clkbuf_2_1__f_clk'], wr |
| IN-02 | neg2 | FAIL | FAIL | FAIL - instances: 352 standard cells in design; missing 5 ['clkbuf_0_clk', 'clkbuf_2_0__f_clk', 'clkbuf_2_1__f_clk'], wr |
| IN-02 | neg3 | FAIL | FAIL | FAIL - module_found: module gcd not found |
| IN-02 | neg4 | FAIL | FAIL | FAIL - instances: 352 standard cells in design; missing 5 ['clkbuf_0_clk', 'clkbuf_2_0__f_clk', 'clkbuf_2_1__f_clk'], wr |
| IN-02 | neg5 | FAIL | FAIL | FAIL - file:outputs/gcd_netlist.v: missing |
| IN-03 | reference | PASS | PASS | PASS (7 checks) |
| IN-03 | empty | FAIL | FAIL | FAIL - file:outputs/cell_usage.txt: missing |
| IN-03 | alt1 | PASS | PASS | PASS (7 checks) |
| IN-03 | alt2 | PASS | PASS | PASS (7 checks) |
| IN-03 | alt3 | PASS | PASS | PASS (7 checks) |
| IN-03 | neg1 | FAIL | FAIL | FAIL - script_completed: invalid_command: Error: agent_script.tcl, 2 invalid command name "report_cell_usage"; file:outp |
| IN-03 | neg2 | FAIL | FAIL | FAIL - cell_types_set: 27 listed, 26 expected; missing [], unexpected ['TAPCELL_X1']; total: total 461, expected 347 |
| IN-03 | neg3 | FAIL | FAIL | FAIL - cell_types_set: 30 listed, 26 expected; missing [], unexpected ['BUF_X1', 'BUF_X2', 'BUF_X4', 'CLKBUF_X1']; total |
| IN-03 | neg4 | FAIL | FAIL | FAIL - total: total 461, expected 347 |
| IN-04 | reference | PASS | PASS | PASS (9 checks) |
| IN-04 | empty | FAIL | FAIL | FAIL - file:outputs/high_fanout_nets.txt: missing |
| IN-04 | alt1 | PASS | PASS | PASS (9 checks) |
| IN-04 | alt2 | PASS | PASS | PASS (9 checks) |
| IN-04 | alt3 | PASS | PASS | PASS (9 checks) |
| IN-04 | neg1 | FAIL | FAIL | FAIL - eligible_nets: not existing or excluded (clock/supply): ['clk']; top_nets: actual fanouts of listed nets [41, 32, |
| IN-04 | neg2 | FAIL | FAIL | FAIL - fanout_values: wrong: _188_ 33 (actual 32), _233_ 17 (actual 16), _236_ 17 (actual 16), _240_ 17 (actual 16) |
| IN-04 | neg3 | FAIL | FAIL | FAIL - eligible_nets: not existing or excluded (clock/supply): ['VSS', 'VDD']; fanout_values: wrong: VSS 460 (actual 0), |
| IN-04 | neg4 | FAIL | FAIL | FAIL - sorted_decreasing: order [16, 16, 16, 32, 41] |
| IN-04 | neg5 | FAIL | FAIL | FAIL - fanout_values: wrong: req_rdy 40 (actual 41) |
| IN-05 | reference | PASS | PASS | PASS (7 checks) |
| IN-05 | empty | FAIL | FAIL | FAIL - file:outputs/floorplan_summary.txt: missing |
| IN-05 | alt1 | PASS | PASS | PASS (7 checks) |
| IN-05 | alt2 | PASS | PASS | PASS (7 checks) |
| IN-05 | alt3 | PASS | PASS | PASS (7 checks) |
| IN-05 | neg1 | FAIL | FAIL | FAIL - cell_area: value 6398.36, target 578.816 +/- 0.01; utilization_percent: value 100, target 9.04631 +/- 0.01 |
| IN-05 | neg2 | FAIL | FAIL | FAIL - cell_area: value 548.49, target 578.816 +/- 0.01; utilization_percent: value 8.57, target 9.04631 +/- 0.01 |
| IN-05 | neg3 | FAIL | FAIL | FAIL - utilization_percent: value 5.73, target 9.04631 +/- 0.01 |
| IN-05 | neg4 | FAIL | FAIL | FAIL - cell_area: value 5.78816e-10, target 578.816 +/- 0.01; utilization_percent: value 0.0904631, target 9.04631 +/- 0 |
| IN-05 | neg5 | FAIL | FAIL | FAIL - die_area: reported [0.0, 0.0, 200260.0, 201600.0], expected [0.0, 0.0, 100.13, 100.8] (+/- 0.01 um); core_area: r |
| IN-05 | neg6 | FAIL | FAIL | FAIL - die_area: reported [0.0, 0.0, 100.0, 100.0], expected [0.0, 0.0, 100.13, 100.8] (+/- 0.01 um); core_area: reporte |
| IN-05 | neg7 | FAIL | FAIL | FAIL - cell_area: value 376, target 578.816 +/- 0.01; utilization_percent: value 5.88, target 9.04631 +/- 0.01 |
| IN-05 | neg8 | FAIL | FAIL | FAIL - design_unchanged: inst_count 1877 -> 490; status_counts {'LOCKED': 114, 'PLACED': 1763} -> {'LOCKED': 114, 'PLACE |
| IN-06 | reference | PASS | PASS | PASS (11 checks) |
| IN-06 | empty | FAIL | FAIL | FAIL - file:outputs/flop_types.txt: missing; file:outputs/flop_clock_drivers.txt: missing |
| IN-06 | alt1 | PASS | PASS | PASS (11 checks) |
| IN-06 | alt2 | PASS | PASS | PASS (11 checks) |
| IN-06 | alt3 | PASS | PASS | PASS (11 checks) |
| IN-06 | neg1 | FAIL | FAIL | FAIL - flop_types_set: 0 listed, 2 expected; missing ['DFF_X1', 'DFF_X2'], unexpected []; flop_types_counts: nothing lis |
| IN-06 | neg2 | FAIL | FAIL | FAIL - clock_drivers_set: 5 listed, 4 expected; missing [], unexpected ['clkbuf_0_clk'] |
| IN-06 | neg3 | FAIL | FAIL | FAIL - clock_drivers_set: 4 listed, 4 expected; missing ['clkbuf_2_0__f_clk', 'clkbuf_2_1__f_clk', 'clkbuf_2_2__f_clk',  |
| IN-06 | neg4 | FAIL | FAIL | FAIL - clock_drivers_set: 5 listed, 4 expected; missing [], unexpected ['clkbuf_0_clk'] |
| IN-06 | neg5 | FAIL | FAIL | FAIL - clock_drivers_set: 39 listed, 4 expected; missing [], unexpected ['_672_', '_673_', '_674_', '_675_', '_676_', '_ |
| OP-01 | reference | PASS | PASS | PASS (8 checks) |
| OP-01 | empty | FAIL | FAIL | FAIL - data_inputs_buffered: 0/35 data inputs drive a single buffer; e.g. req_msg[0] -> 1/MUX2_X1, req_msg[10] -> 1/MUX2 |
| OP-01 | alt1 | PASS | PASS | PASS (8 checks) |
| OP-01 | alt2 | PASS | PASS | PASS (8 checks) |
| OP-01 | alt3 | PASS | PASS | PASS (8 checks) |
| OP-01 | neg1 | FAIL | FAIL | FAIL - outputs_unbuffered: 0/18 output ports keep their original driver; e.g. req_rdy now driven by output36 |
| OP-01 | neg2 | FAIL | FAIL | FAIL - data_inputs_buffered: 0/35 data inputs drive a single buffer; e.g. req_msg[0] -> 1/MUX2_X1, req_msg[10] -> 1/MUX2 |
| OP-01 | neg3 | FAIL | FAIL | FAIL - all_cells_placed: 347/382 placed |
| OP-01 | neg4 | FAIL | FAIL | FAIL - clock_tree_unchanged: clock network changed at 36 points (e.g. _672_/CK: PORT:clk -> in_buf_0:BUF_X2>PORT:clk) |
| OP-01 | neg5 | FAIL | FAIL | FAIL - cells_inside_core: 35 cells outside the core |
| OP-01 | neg6 | FAIL | FAIL | FAIL - data_inputs_buffered: 33/35 data inputs drive a single buffer; e.g. req_val -> 2/BUF_X1,BUF_X1, reset -> 3/BUF_X1 |
| OP-02 | reference | PASS | PASS | PASS (9 checks) |
| OP-02 | empty | FAIL | FAIL | FAIL - hold_slack_margin: worst hold slack 0.0531 ns (start 0.0531, required >= 0.08) |
| OP-02 | alt1 | PASS | PASS | PASS (9 checks) |
| OP-02 | alt2 | PASS | PASS | PASS (9 checks) |
| OP-02 | alt3 | PASS | PASS | PASS (9 checks) |
| OP-02 | alt4 | PASS | PASS | PASS (9 checks) |
| OP-02 | alt5 | PASS | PASS | PASS (9 checks) |
| OP-02 | neg1 | FAIL | FAIL | FAIL - hold_slack_margin: worst hold slack 0.0531 ns (start 0.0531, required >= 0.08) |
| OP-02 | neg2 | FAIL | FAIL | FAIL - hold_slack_margin: worst hold slack 0.0531 ns (start 0.0531, required >= 0.08) |
| OP-02 | neg3 | FAIL | FAIL | FAIL - placement_legal: check_placement legal=False |
| OP-02 | neg4 | FAIL | FAIL | FAIL - hold_slack_margin: worst hold slack 0.0531 ns (start 0.0531, required >= 0.08) |
| OP-02 | neg5 | FAIL | FAIL | FAIL - setup_not_degraded: worst setup slack -0.1165 ns (start -0.0975, allowed >= -0.1025) |
| OP-02 | neg6 | FAIL | FAIL | FAIL - hold_slack_margin: worst hold slack 0.0531 ns (start 0.0531, required >= 0.08) |
| OP-02 | neg7 | FAIL | FAIL | FAIL - setup_not_degraded: worst setup slack -0.1457 ns (start -0.0975, allowed >= -0.1025); clock_tree_unchanged: clock |
| OP-03 | reference | PASS | PASS | PASS (9 checks) |
| OP-03 | empty | FAIL | FAIL | FAIL - worst_setup_slack: WNS -0.0975 ns (start -0.0975, required >= -0.06); total_negative_setup_slack: TNS -0.4810 ns  |
| OP-03 | alt1 | PASS | PASS | PASS (9 checks) |
| OP-03 | alt2 | PASS | PASS | PASS (9 checks) |
| OP-03 | alt3 | PASS | PASS | PASS (9 checks) |
| OP-03 | alt4 | PASS | PASS | PASS (9 checks) |
| OP-03 | alt5 | PASS | PASS | PASS (9 checks) |
| OP-03 | alt6 | PASS | PASS | PASS (9 checks) |
| OP-03 | neg1 | FAIL | FAIL | FAIL - total_negative_setup_slack: TNS -0.6358 ns (start -0.4810, required >= -0.4) |
| OP-03 | neg2 | FAIL | FAIL | FAIL - worst_setup_slack: WNS -0.0975 ns (start -0.0975, required >= -0.06); total_negative_setup_slack: TNS -0.4810 ns  |
| OP-03 | neg3 | FAIL | FAIL | FAIL - placement_legal: check_placement legal=False |
| OP-03 | neg4 | FAIL | FAIL | FAIL - total_negative_setup_slack: TNS -0.6256 ns (start -0.4810, required >= -0.4) |
| OP-03 | neg5 | FAIL | FAIL | FAIL - worst_setup_slack: WNS -0.0975 ns (start -0.0975, required >= -0.06); total_negative_setup_slack: TNS -0.5199 ns  |
| OP-03 | neg6 | FAIL | FAIL | FAIL - total_negative_setup_slack: TNS -0.6358 ns (start -0.4810, required >= -0.4) |
| OP-03 | neg7 | FAIL | FAIL | FAIL - clock_tree_unchanged: clock network changed at 36 points (e.g. _672_/CK: clkbuf_2_3__f_clk:BUF_X4>clkbuf_0_clk:BU |
| OP-04 | reference | PASS | PASS | PASS (7 checks) |
| OP-04 | empty | FAIL | FAIL | FAIL - violations_repaired: remaining max_slew 76, max_capacitance 22, max_fanout 5 (before 76, 22, 5; allowed: 0 slew,  |
| OP-04 | alt1 | PASS | PASS | PASS (7 checks) |
| OP-04 | alt2 | PASS | PASS | PASS (7 checks) |
| OP-04 | alt3 | PASS | PASS | PASS (7 checks) |
| OP-04 | alt4 | PASS | PASS | PASS (7 checks) |
| OP-04 | neg1 | FAIL | FAIL | FAIL - reported_counts_match: max_capacitance reported 22 0, actual 22 5 |
| OP-04 | neg2 | FAIL | FAIL | FAIL - violations_repaired: remaining max_slew 0, max_capacitance 18, max_fanout 0 (before 76, 22, 5; allowed: 0 slew, < |
| OP-04 | neg3 | FAIL | FAIL | FAIL - reported_counts_match: max_capacitance reported 22 6, actual 22 5 |
| OP-04 | neg4 | FAIL | FAIL | FAIL - reported_counts_match: max_slew reported 0 0, actual 76 0 |
| OP-04 | neg5 | FAIL | FAIL | FAIL - reported_counts_match: max_capacitance reported 383 767, actual 22 1 |
| OP-04 | neg6 | FAIL | FAIL | FAIL - reported_counts_match: max_slew reported 1 0, actual 76 0; max_capacitance reported 1 1, actual 22 5; max_fanout  |
| OP-04 | neg7 | FAIL | FAIL | FAIL - reported_counts_match: max_slew reported 0 0, actual 76 0; max_capacitance reported 0 5, actual 22 5; max_fanout  |
| PL-01 | reference | PASS | PASS | PASS (7 checks) |
| PL-01 | empty | FAIL | FAIL | FAIL - all_cells_placed: 0/347 placed; cells_spread: bin density -1.000 (<= 1.2; stacked cells give > 5) |
| PL-01 | alt1 | PASS | PASS | PASS (7 checks) |
| PL-01 | alt2 | PASS | PASS | PASS (7 checks) |
| PL-01 | alt3 | PASS | PASS | PASS (7 checks) |
| PL-01 | neg1 | FAIL | FAIL | FAIL - all_cells_placed: 0/347 placed; cells_spread: bin density -1.000 (<= 1.2; stacked cells give > 5); wirelength_vs_ |
| PL-01 | neg2 | FAIL | FAIL | FAIL - cells_spread: bin density 8.975 (<= 1.2; stacked cells give > 5) |
| PL-01 | neg3 | FAIL | FAIL | FAIL - all_cells_placed: 0/347 placed; cells_spread: bin density -1.000 (<= 1.2; stacked cells give > 5) |
| PL-01 | neg4 | FAIL | FAIL | FAIL - cells_spread: bin density 27.181 (<= 1.2; stacked cells give > 5) |
| PL-01 | neg5 | FAIL | FAIL | FAIL - wirelength_vs_reference: HPWL 11535.5 um, limit 7112.2 um (1.5 x reference 4741.5 um) |
| PL-01 | neg6 | FAIL | FAIL | FAIL - cells_spread: bin density 6.439 (<= 1.2; stacked cells give > 5) |
| PL-02 | reference | PASS | PASS | PASS (6 checks) |
| PL-02 | empty | FAIL | FAIL | FAIL - placement_legal: check_placement legal=False; row_orientation: 346 cells off-row or with an orientation not match |
| PL-02 | alt1 | PASS | PASS | PASS (6 checks) |
| PL-02 | alt2 | PASS | PASS | PASS (6 checks) |
| PL-02 | alt3 | PASS | PASS | PASS (6 checks) |
| PL-02 | neg1 | FAIL | FAIL | FAIL - near_global_placement: 347/347 cells compared, max 40.06 um (<= 10.0), mean 12.09 um (<= 2.0) |
| PL-02 | neg2 | FAIL | FAIL | FAIL - placement_legal: check_placement legal=False; near_global_placement: 347/347 cells compared, max 25.39 um (<= 10. |
| PL-02 | neg3 | FAIL | FAIL | FAIL - placement_legal: check_placement legal=False; row_orientation: 347 cells off-row or with an orientation not match |
| PL-02 | neg4 | FAIL | FAIL | FAIL - near_global_placement: 347/347 cells compared, max 38.80 um (<= 10.0), mean 2.11 um (<= 2.0) |
| PL-02 | neg5 | FAIL | FAIL | FAIL - placement_legal: check_placement legal=False |
| PL-03 | reference | PASS | PASS | PASS (5 checks) |
| PL-03 | empty | FAIL | FAIL | FAIL - file:utilization.txt: missing; utilization_value: reported n/a %, actual 8.182 % (+/- 0.02); above_target_decisio |
| PL-03 | alt1 | PASS | PASS | PASS (5 checks) |
| PL-03 | alt2 | PASS | PASS | PASS (5 checks) |
| PL-03 | alt3 | PASS | PASS | PASS (5 checks) |
| PL-03 | neg1 | FAIL | FAIL | FAIL - utilization_value: reported 7.710 %, actual 8.182 % (+/- 0.02) |
| PL-03 | neg2 | FAIL | FAIL | FAIL - utilization_value: reported 8.000 %, actual 8.182 % (+/- 0.02) |
| PL-03 | neg3 | FAIL | FAIL | FAIL - utilization_value: reported 65.000 %, actual 8.182 % (+/- 0.02) |
| PL-03 | neg4 | FAIL | FAIL | FAIL - above_target_decision: reported yes, expected no (8.18 % vs target 70.0 %) |
| PL-03 | neg5 | FAIL | FAIL | FAIL - utilization_value: reported 5.190 %, actual 8.182 % (+/- 0.02) |
| PL-03 | neg6 | FAIL | FAIL | FAIL - utilization_value: reported 0.080 %, actual 8.182 % (+/- 0.02) |
| PL-04 | reference | PASS | PASS | PASS (8 checks) |
| PL-04 | empty | FAIL | FAIL | FAIL - all_cells_placed: 0/347 placed; cells_spread: bin density -1.000 (<= 1.2; stacked cells give > 5); target_density |
| PL-04 | alt1 | PASS | PASS | PASS (8 checks) |
| PL-04 | alt2 | PASS | PASS | PASS (8 checks) |
| PL-04 | alt3 | PASS | PASS | PASS (8 checks) |
| PL-04 | alt4 | PASS | PASS | PASS (8 checks) |
| PL-04 | neg1 | FAIL | FAIL | FAIL - target_density: measured placement density 0.680, expected 0.44..0.55 |
| PL-04 | neg2 | FAIL | FAIL | FAIL - target_density: measured placement density 0.680, expected 0.44..0.55 |
| PL-04 | neg3 | FAIL | FAIL | FAIL - target_density: measured placement density 0.316, expected 0.44..0.55 |
| PL-04 | neg4 | FAIL | FAIL | FAIL - target_density: measured placement density 0.305, expected 0.44..0.55 |
| PL-05 | reference | PASS | PASS | PASS (8 checks) |
| PL-05 | empty | FAIL | FAIL | FAIL - placement_legal: check_placement legal=False; row_orientation: 346 cells off-row or with an orientation not match |
| PL-05 | alt1 | PASS | PASS | PASS (8 checks) |
| PL-05 | alt2 | PASS | PASS | PASS (8 checks) |
| PL-05 | alt3 | PASS | PASS | PASS (8 checks) |
| PL-05 | alt4 | PASS | PASS | PASS (8 checks) |
| PL-05 | neg1 | FAIL | FAIL | FAIL - gap_between_cells: smallest gap between adjacent standard cells 2.00 sites over 305 pairs (>= 4) |
| PL-05 | neg2 | FAIL | FAIL | FAIL - gap_between_cells: smallest gap between adjacent standard cells 0.00 sites over 304 pairs (>= 4) |
| PL-05 | neg3 | FAIL | FAIL | FAIL - gap_between_cells: smallest gap between adjacent standard cells 0.00 sites over 305 pairs (>= 4) |
| PL-05 | neg4 | FAIL | FAIL | FAIL - gap_between_cells: smallest gap between adjacent standard cells 2.00 sites over 305 pairs (>= 4) |
| PL-05 | neg5 | FAIL | FAIL | FAIL - near_global_placement: 347/347 cells compared, max 40.06 um (<= 10.0), mean 11.72 um (<= 2.0) |
| PL-06 | reference | PASS | PASS | PASS (7 checks) |
| PL-06 | empty | FAIL | FAIL | FAIL - no_empty_sites: 21878 of 24054 row sites not covered by any cell (57/57 rows); fillers_inserted: 0 filler instanc |
| PL-06 | alt1 | PASS | PASS | PASS (7 checks) |
| PL-06 | alt2 | PASS | PASS | PASS (7 checks) |
| PL-06 | alt3 | PASS | PASS | PASS (7 checks) |
| PL-06 | alt4 | PASS | PASS | PASS (7 checks) |
| PL-06 | alt5 | PASS | PASS | PASS (7 checks) |
| PL-06 | neg1 | FAIL | FAIL | FAIL - filler_name_prefix: 0/1387 filler instances named 'FILL_*' |
| PL-06 | neg2 | FAIL | FAIL | FAIL - script_completed: runtime_failure: OpenROAD exited abnormally (exit code -11, script status unknown); design_stat |
| PL-06 | neg3 | FAIL | FAIL | FAIL - script_completed: tool_error: [ERROR DPL-0039] "FILLER*" did not match any masters.; no_empty_sites: 21878 of 240 |
| PL-06 | neg4 | FAIL | FAIL | FAIL - filler_name_prefix: 0/1387 filler instances named 'FILL_*' |
| PL-07 | reference | PASS | PASS | PASS (9 checks) |
| PL-07 | empty | FAIL | FAIL | FAIL - cells_mirrored: 0 cells changed orientation; hpwl_reduced: HPWL 4554.6 -> 4554.6 um, reduction 0.00 % (>= 1.0 %) |
| PL-07 | alt1 | PASS | PASS | PASS (9 checks) |
| PL-07 | alt2 | PASS | PASS | PASS (9 checks) |
| PL-07 | alt3 | PASS | PASS | PASS (9 checks) |
| PL-07 | neg1 | FAIL | FAIL | FAIL - no_cell_moved: 244 of 347/347 cells changed location |
| PL-07 | neg2 | FAIL | FAIL | FAIL - hpwl_reduced: HPWL 4554.6 -> 4638.9 um, reduction -1.85 % (>= 1.0 %) |
| PL-07 | neg3 | FAIL | FAIL | FAIL - cells_mirrored: 0 cells changed orientation; hpwl_reduced: HPWL 4554.6 -> 4554.6 um, reduction 0.00 % (>= 1.0 %) |
| PL-07 | neg4 | FAIL | FAIL | FAIL - y_axis_mirror_only: 140 orientation changes are not Y-axis mirrors; hpwl_reduced: HPWL 4554.6 -> 4521.3 um, reduc |
| PL-07 | neg5 | FAIL | FAIL | FAIL - io_pins_unchanged: 31 of 54 IO pins moved or changed (54 now) |
| PL-07 | neg6 | FAIL | FAIL | FAIL - no_cell_moved: 116 of 347/347 cells changed location; cells_mirrored: 0 cells changed orientation; placement_lega |
| PL-08 | reference | PASS | PASS | PASS (11 checks) |
| PL-08 | empty | FAIL | FAIL | FAIL - file:hpwl.txt: missing; hpwl_reduced: HPWL 4554.6 -> 4554.6 um, reduction 0.00 % (>= 3.0 %); report_hpwl_before_u |
| PL-08 | alt1 | PASS | PASS | PASS (11 checks) |
| PL-08 | alt2 | PASS | PASS | PASS (11 checks) |
| PL-08 | neg1 | FAIL | FAIL | FAIL - hpwl_reduced: HPWL 4554.6 -> 4492.0 um, reduction 1.38 % (>= 3.0 %) |
| PL-08 | neg2 | FAIL | FAIL | FAIL - report_hpwl_before_um: reported 5619.65, actual 4554.61 um (+/- 0.5 %); report_hpwl_after_um: reported 5378.75, a |
| PL-08 | neg3 | FAIL | FAIL | FAIL - report_hpwl_before_um: reported 4263.19, actual 4554.61 um (+/- 0.5 %) |
| PL-08 | neg4 | FAIL | FAIL | FAIL - report_hpwl_before_um: reported 5000.00, actual 4554.61 um (+/- 0.5 %); report_hpwl_after_um: reported 4600.00, a |
| PL-08 | neg5 | FAIL | FAIL | FAIL - report_hpwl_before_um: reported 4438.63, actual 4554.61 um (+/- 0.5 %); report_hpwl_after_um: reported 4149.82, a |
| PL-08 | neg6 | FAIL | FAIL | FAIL - io_pins_unchanged: 42 of 54 IO pins moved or changed (54 now) |
| PL-08 | neg7 | FAIL | FAIL | FAIL - refines_existing_placement: 347/347 cells compared, mean movement 12.16 um (<= 5.0) |
| PL-09 | reference | PASS | PASS | PASS (11 checks) |
| PL-09 | empty | FAIL | FAIL | FAIL - placement_legal: check_placement legal=False; file:top_displaced.txt: missing; report_entries: 0 '<cell> <value>' |
| PL-09 | alt1 | PASS | PASS | PASS (11 checks) |
| PL-09 | alt2 | PASS | PASS | PASS (11 checks) |
| PL-09 | alt3 | PASS | PASS | PASS (11 checks) |
| PL-09 | neg1 | FAIL | FAIL | FAIL - report_values: _465_: 1.9760 vs 1.9835; _516_: 1.9640 vs 1.9840; _468_: 1.9490 vs 2.0295; report_is_top_n: 0/5 re |
| PL-09 | neg2 | FAIL | FAIL | FAIL - report_values: _597_: 4761.0000 vs 2.3805; _542_: 4542.0000 vs 2.2710; _443_: 4487.0000 vs 2.2435 |
| PL-09 | neg3 | FAIL | FAIL | FAIL - report_values: _345_: 2.5000 vs 0.6515; _347_: 2.2500 vs 2.0185; _348_: 2.0000 vs 0.9650; report_is_top_n: 0/5 re |
| PL-09 | neg4 | FAIL | FAIL | FAIL - report_is_top_n: 0/5 reported cells among the 5 largest displacements (n-th largest 2.2080 um); report_sorted: la |
| PL-09 | neg5 | FAIL | FAIL | FAIL - report_values: _443_: 3.6430 vs 2.2435; _665_: 3.4870 vs 2.0875; _573_: 3.4560 vs 2.0560; report_is_top_n: 1/5 re |
| PL-09 | neg6 | FAIL | FAIL | FAIL - near_global_placement: 347/347 cells compared, max 40.06 um (<= 10.0), mean 12.09 um (<= 2.0); report_values: _45 |
| PL-10 | reference | PASS | PASS | PASS (12 checks) |
| PL-10 | empty | FAIL | FAIL | FAIL - all_cells_placed: 0/347 placed; placement_legal: check_placement legal=None; io_pins_replaced: 0/54 IO pins moved |
| PL-10 | alt1 | PASS | PASS | PASS (12 checks) |
| PL-10 | alt2 | PASS | PASS | PASS (12 checks) |
| PL-10 | alt3 | PASS | PASS | PASS (12 checks) |
| PL-10 | alt4 | PASS | PASS | PASS (12 checks) |
| PL-10 | alt5 | PASS | PASS | PASS (12 checks) |
| PL-10 | neg1 | FAIL | FAIL | FAIL - io_pins_replaced: 0/54 IO pins moved from their starting positions (>= 50%); io_net_wirelength: 2822.4 um, limit  |
| PL-10 | neg2 | FAIL | FAIL | FAIL - io_pins_replaced: 0/54 IO pins moved from their starting positions (>= 50%); io_net_wirelength: 2822.4 um, limit  |
| PL-10 | neg3 | FAIL | FAIL | FAIL - gap_between_cells: smallest gap between adjacent standard cells 0.00 sites (>= 2) |
| PL-10 | neg4 | FAIL | FAIL | FAIL - gap_between_cells: smallest gap between adjacent standard cells 0.00 sites (>= 2) |
| PL-10 | neg5 | FAIL | FAIL | FAIL - io_pin_layers: 0 pins off the die boundary, 26 on the wrong layer (left/right metal3, top/bottom metal2) |
| PL-10 | neg6 | FAIL | FAIL | FAIL - placement_legal: check_placement legal=False; row_orientation: 347 cells off-row or with an orientation not match |
| RT-01 | reference | PASS | PASS | PASS (4 checks) |
| RT-01 | empty | FAIL | FAIL | FAIL - all_nets_globally_routed: 0/389 routable nets have route guides (389 in the starting state); file:outputs/gcd.gui |
| RT-01 | alt1 | PASS | PASS | PASS (4 checks) |
| RT-01 | alt2 | PASS | PASS | PASS (4 checks) |
| RT-01 | alt3 | PASS | PASS | PASS (4 checks) |
| RT-01 | neg1 | FAIL | FAIL | FAIL - file:outputs/gcd.guide: empty |
| RT-01 | neg2 | FAIL | FAIL | FAIL - file:outputs/gcd.guide: empty |
| RT-01 | neg3 | FAIL | FAIL | FAIL - file:outputs/gcd.guide: missing |
| RT-01 | neg4 | FAIL | FAIL | FAIL - all_nets_globally_routed: 6/389 routable nets have route guides (389 in the starting state) |
| RT-01 | neg5 | FAIL | FAIL | FAIL - file:outputs/gcd.guide: not a route-guide file: bad guide coordinates '73.5 75.6 75.6 77.7 metal1' |
| RT-01 | neg6 | FAIL | FAIL | FAIL - file:outputs/gcd.guide: missing |
| RT-01 | neg7 | FAIL | FAIL | FAIL - guide_file_matches_routing: 389 guided nets in the database, 389 compared; missing 0, extra 0, different boxes 26 |
| RT-02 | reference | PASS | PASS | PASS (5 checks) |
| RT-02 | empty | FAIL | FAIL | FAIL - all_nets_globally_routed: 0/389 routable nets have route guides (389 in the starting state); report:outputs/grt_w |
| RT-02 | alt1 | PASS | PASS | PASS (5 checks) |
| RT-02 | alt2 | PASS | PASS | PASS (5 checks) |
| RT-02 | neg1 | FAIL | FAIL | FAIL - total_global_route_wirelength: value 4727.91, target 7730.1 +/- 38.7 |
| RT-02 | neg2 | FAIL | FAIL | FAIL - total_global_route_wirelength: value 9795.7, target 7730.1 +/- 38.7 |
| RT-02 | neg3 | FAIL | FAIL | FAIL - all_nets_globally_routed: 0/389 routable nets have route guides (389 in the starting state); total_global_route_w |
| RT-02 | neg4 | FAIL | FAIL | FAIL - total_global_route_wirelength: value 7217.7, target 7730.1 +/- 38.7 |
| RT-02 | neg5 | FAIL | FAIL | FAIL - report:outputs/grt_wirelength.txt: expected exactly one number, found 860: 'tool net total_wl #pins \ngrt: _000_  |
| RT-02 | neg6 | FAIL | FAIL | FAIL - total_global_route_wirelength: value 7.736, target 7730.1 +/- 38.7 |
| RT-02 | neg7 | FAIL | FAIL | FAIL - total_global_route_wirelength: value 5820.52, target 7734.3 +/- 38.7 |
| RT-03 | reference | PASS | PASS | PASS (5 checks) |
| RT-03 | empty | FAIL | FAIL | FAIL - all_nets_globally_routed: 0/389 routable nets have route guides (389 in the starting state); clock_routing_layers |
| RT-03 | alt1 | PASS | PASS | PASS (5 checks) |
| RT-03 | alt2 | PASS | PASS | PASS (5 checks) |
| RT-03 | alt3 | PASS | PASS | PASS (5 checks) |
| RT-03 | alt4 | PASS | PASS | PASS (5 checks) |
| RT-03 | neg1 | FAIL | FAIL | FAIL - signal_routing_layers: 262 nets with wires outside metal2-metal6 (e.g. _001_:metal1, _003_:metal1, _006_:metal1); |
| RT-03 | neg2 | FAIL | FAIL | FAIL - clock_routing_layers: 2 clock-tree nets checked; 2 with wires outside metal4-metal6 (clknet_0_clk:metal2/metal3,  |
| RT-03 | neg3 | FAIL | FAIL | FAIL - clock_routing_layers: 2 clock-tree nets checked; 1 with wires outside metal4-metal6 (clknet_0_clk:metal7) |
| RT-03 | neg4 | FAIL | FAIL | FAIL - signal_routing_layers: 267 nets with wires outside metal2-metal6 (e.g. _001_:metal1, _003_:metal1, _006_:metal1) |
| RT-03 | neg5 | FAIL | FAIL | FAIL - all_nets_globally_routed: 6/389 routable nets have route guides (389 in the starting state) |
| RT-04 | reference | PASS | PASS | PASS (5 checks) |
| RT-04 | empty | FAIL | FAIL | FAIL - report:outputs/wns_grt.txt: missing |
| RT-04 | alt1 | PASS | PASS | PASS (5 checks) |
| RT-04 | alt2 | PASS | PASS | PASS (5 checks) |
| RT-04 | alt3 | PASS | PASS | PASS (5 checks) |
| RT-04 | alt4 | PASS | PASS | PASS (5 checks) |
| RT-04 | neg1 | FAIL | FAIL | FAIL - worst_setup_slack_ns: value -0.0518, target -0.0593623 +/- 0.0005 |
| RT-04 | neg2 | FAIL | FAIL | FAIL - worst_setup_slack_ns: value -0.0377, target -0.0593623 +/- 0.0005 |
| RT-04 | neg3 | FAIL | FAIL | FAIL - worst_setup_slack_ns: value 0.0514, target -0.0593623 +/- 0.0005 |
| RT-04 | neg4 | FAIL | FAIL | FAIL - existing_global_routing_kept: 413 guided nets in the database, 413 compared; missing 0, extra 0, different boxes  |
| RT-04 | neg5 | FAIL | FAIL | FAIL - worst_setup_slack_ns: value -0.06, target -0.0593623 +/- 0.0005 |
| RT-04 | neg6 | FAIL | FAIL | FAIL - worst_setup_slack_ns: value 0.4556, target -0.0593623 +/- 0.0005 |
| RT-04 | neg7 | FAIL | FAIL | FAIL - worst_setup_slack_ns: value -0.0585, target -0.0593623 +/- 0.0005 |
| RT-05 | reference | PASS | PASS | PASS (5 checks) |
| RT-05 | empty | FAIL | FAIL | FAIL - all_nets_detail_routed: 0/413 routable nets have detailed routing (413 in the starting state); no_drc_violations: |
| RT-05 | alt1 | PASS | PASS | PASS (5 checks) |
| RT-05 | alt2 | PASS | PASS | PASS (5 checks) |
| RT-05 | alt3 | PASS | PASS | PASS (5 checks) |
| RT-05 | alt4 | PASS | PASS | PASS (5 checks) |
| RT-05 | neg1 | FAIL | FAIL | FAIL - no_drc_violations: detailed router reports 1 violations |
| RT-05 | neg2 | FAIL | FAIL | FAIL - all_nets_detail_routed: 0/413 routable nets have detailed routing (413 in the starting state); no_drc_violations: |
| RT-05 | neg3 | FAIL | FAIL | FAIL - file:outputs/route_drc.rpt: missing |
| RT-05 | neg4 | FAIL | FAIL | FAIL - no_drc_violations: detailed router reports 1 violations; drc_report_matches_router: 0 violations listed in the re |
| RT-06 | reference | PASS | PASS | PASS (5 checks) |
| RT-06 | empty | FAIL | FAIL | FAIL - file:outputs/clock_gr_wirelength.txt: missing |
| RT-06 | alt1 | PASS | PASS | PASS (5 checks) |
| RT-06 | alt2 | PASS | PASS | PASS (5 checks) |
| RT-06 | alt3 | PASS | PASS | PASS (5 checks) |
| RT-06 | alt4 | PASS | PASS | PASS (5 checks) |
| RT-06 | alt5 | PASS | PASS | PASS (5 checks) |
| RT-06 | neg1 | FAIL | FAIL | FAIL - clock_nets_reported: 0/6 clock nets reported; missing ['clk', 'clknet_0_clk', 'clknet_2_0__leaf_clk', 'clknet_2_1 |
| RT-06 | neg2 | FAIL | FAIL | FAIL - existing_global_routing_kept: 413 guided nets in the database, 413 compared; missing 0, extra 0, different boxes  |
| RT-06 | neg3 | FAIL | FAIL | FAIL - clock_nets_reported: 4/6 clock nets reported; missing ['clk', 'clknet_0_clk'], non-clock nets [] |
| RT-06 | neg4 | FAIL | FAIL | FAIL - clock_nets_reported: 6/6 clock nets reported; missing [], non-clock nets ['_000_', '_001_', '_002_', '_003_'] |
| RT-06 | neg5 | FAIL | FAIL | FAIL - clock_net_wirelengths: 0/6 values within 0.05 um; wrong: clk=77.03 (expected 67.2), clknet_0_clk=136.5 (expected  |
| RT-06 | neg6 | FAIL | FAIL | FAIL - clock_net_wirelengths: 0/6 values within 0.05 um; wrong: clk=65.9275 (expected 67.2), clknet_0_clk=42.685 (expect |
| RT-07 | reference | PASS | PASS | PASS (7 checks) |
| RT-07 | empty | FAIL | FAIL | FAIL - file:outputs/gcd.spef: missing; report:outputs/wns_rcx.txt: missing |
| RT-07 | alt1 | PASS | PASS | PASS (7 checks) |
| RT-07 | alt2 | PASS | PASS | PASS (7 checks) |
| RT-07 | alt3 | PASS | PASS | PASS (7 checks) |
| RT-07 | neg1 | FAIL | FAIL | FAIL - worst_setup_slack_ns: value -0.0377, target -0.053565 +/- 0.0005 |
| RT-07 | neg2 | FAIL | FAIL | FAIL - file:outputs/gcd.spef: missing; worst_setup_slack_ns: value -0.0594, target -0.053565 +/- 0.0005 |
| RT-07 | neg3 | FAIL | FAIL | FAIL - worst_setup_slack_ns: value -0.0518, target -0.053565 +/- 0.0005 |
| RT-07 | neg4 | FAIL | FAIL | FAIL - worst_setup_slack_ns: value 0.0512, target -0.053565 +/- 0.0005 |
| RT-07 | neg5 | FAIL | FAIL | FAIL - file:outputs/gcd.spef: missing; worst_setup_slack_ns: value -0.0377, target -0.053565 +/- 0.0005 |
| RT-07 | neg6 | FAIL | FAIL | FAIL - worst_setup_slack_ns: value -0.05, target -0.053565 +/- 0.0005 |
| RT-07 | neg7 | FAIL | FAIL | FAIL - routing_unchanged: routed nets 413/413, wirelength 11528.52/5753.385 um; spef_capacitance: 3/413 nets within 10%  |
| RT-08 | reference | PASS | PASS | PASS (7 checks) |
| RT-08 | empty | FAIL | FAIL | FAIL - file:outputs/gcd_route.def: missing |
| RT-08 | alt1 | PASS | PASS | PASS (7 checks) |
| RT-08 | alt2 | PASS | PASS | PASS (7 checks) |
| RT-08 | alt3 | PASS | PASS | PASS (7 checks) |
| RT-08 | neg1 | FAIL | FAIL | FAIL - def_header: VERSION None, DESIGN None, UNITS None; def_components: None components in DEF, 1877 instances in the  |
| RT-08 | neg2 | FAIL | FAIL | FAIL - def_header: VERSION None, DESIGN None, UNITS None; def_components: None components in DEF, 1877 instances in the  |
| RT-08 | neg3 | FAIL | FAIL | FAIL - def_routed_nets: 0 nets with routing in DEF, 413 routed nets in the routed design; def_wirelength_um: value 0, ta |
| RT-08 | neg4 | FAIL | FAIL | FAIL - def_header: VERSION None, DESIGN None, UNITS None; def_components: None components in DEF, 1877 instances in the  |
| RT-08 | neg5 | FAIL | FAIL | FAIL - def_components: 490 components in DEF, 1877 instances in the routed design |
| RT-08 | neg6 | FAIL | FAIL | FAIL - def_routed_nets: 0 nets with routing in DEF, 413 routed nets in the routed design; def_wirelength_um: value 0, ta |
| TA-01 | reference | PASS | PASS | PASS (10 checks) |
| TA-01 | empty | FAIL | FAIL | FAIL - file:outputs/hold_paths.rpt: missing |
| TA-01 | alt1 | PASS | PASS | PASS (10 checks) |
| TA-01 | alt2 | PASS | PASS | PASS (10 checks) |
| TA-01 | alt3 | PASS | PASS | PASS (10 checks) |
| TA-01 | alt4 | PASS | PASS | PASS (10 checks) |
| TA-01 | neg1 | FAIL | FAIL | FAIL - path_type: found Path Type ['max'], expected min; worst_endpoints: not among the 3 worst: resp_msg[13], resp_msg[ |
| TA-01 | neg2 | FAIL | FAIL | FAIL - worst_endpoints: not among the 3 worst: _706_; slacks_match_ground_truth: _674_: 0.0531 vs 0.05944; _672_: 0.0540 |
| TA-01 | neg3 | FAIL | FAIL | FAIL - path_count: 1 paths reported, 3 required; worst_endpoints: missing worst endpoints: _672_ |
| TA-01 | neg4 | FAIL | FAIL | FAIL - slacks_match_ground_truth: _674_: 0.0612 vs 0.05944; _672_: 0.0634 vs 0.06084; _693_: 0.0671 vs 0.06816 |
| TA-01 | neg5 | FAIL | FAIL | FAIL - one_path_per_endpoint: repeated endpoints ['_674_']; slacks_match_ground_truth: _674_: 0.0613 vs 0.05944 |
| TA-01 | neg6 | FAIL | FAIL | FAIL - full_path_detail: paths without pin-by-pin detail: [1, 2, 3]; report_precision: slack decimals [], need >= 4; sla |
| TA-01 | neg7 | FAIL | FAIL | FAIL - worst_endpoints: not among the 3 worst: _673_; slacks_match_ground_truth: _674_: 0.1053 vs 0.05944; _673_: 0.1064 |
| TA-02 | reference | PASS | PASS | PASS (11 checks) |
| TA-02 | empty | FAIL | FAIL | FAIL - file:outputs/reset_setup_path.rpt: missing |
| TA-02 | alt1 | PASS | PASS | PASS (11 checks) |
| TA-02 | alt2 | PASS | PASS | PASS (11 checks) |
| TA-02 | alt3 | PASS | PASS | PASS (11 checks) |
| TA-02 | neg1 | FAIL | FAIL | FAIL - startpoint: startpoints _697_, required reset; worst_endpoints: unknown endpoints resp_msg[15]; slacks_match_grou |
| TA-02 | neg2 | FAIL | FAIL | FAIL - path_count: 0 paths reported, 1 required |
| TA-02 | neg3 | FAIL | FAIL | FAIL - path_type: found Path Type ['min'], expected max; slacks_match_ground_truth: _674_: 0.1053 vs 0.27337 |
| TA-02 | neg4 | FAIL | FAIL | FAIL - report_precision: slack decimals ['2'], need >= 4 |
| TA-02 | neg5 | FAIL | FAIL | FAIL - slacks_match_ground_truth: _674_: 0.2697 vs 0.27337 |
| TA-02 | neg6 | FAIL | FAIL | FAIL - path_count: 3 paths reported, 1 required; one_path_per_endpoint: repeated endpoints ['_674_']; slacks_match_groun |
| TA-03 | reference | PASS | PASS | PASS (5 checks) |
| TA-03 | empty | FAIL | FAIL | FAIL - file:outputs/clock_skew.rpt: missing |
| TA-03 | alt1 | PASS | PASS | PASS (5 checks) |
| TA-03 | alt2 | PASS | PASS | PASS (5 checks) |
| TA-03 | alt3 | PASS | PASS | PASS (5 checks) |
| TA-03 | alt4 | PASS | PASS | PASS (5 checks) |
| TA-03 | neg1 | FAIL | FAIL | FAIL - skew_matches_ground_truth: stated skew values ['0.00'] vs ground truth 0.00182 ns (>= 4 decimals) |
| TA-03 | neg2 | FAIL | FAIL | FAIL - skew_matches_ground_truth: stated skew values ['0.0032'] vs ground truth 0.00182 ns (>= 4 decimals) |
| TA-03 | neg3 | FAIL | FAIL | FAIL - mentions_skew: no skew value in file; skew_matches_ground_truth: stated skew values [] vs ground truth 0.00182 ns |
| TA-03 | neg4 | FAIL | FAIL | FAIL - skew_matches_ground_truth: stated skew values ['0.0042'] vs ground truth 0.00182 ns (>= 4 decimals) |
| TA-03 | neg5 | FAIL | FAIL | FAIL - skew_matches_ground_truth: stated skew values ['1.8232'] vs ground truth 0.00182 ns (>= 4 decimals) |
| TA-03 | neg6 | FAIL | FAIL | FAIL - skew_matches_ground_truth: stated skew values ['0.0018', '0.0032'] vs ground truth 0.00182 ns (>= 4 decimals) |
| TA-04 | reference | PASS | PASS | PASS (10 checks) |
| TA-04 | empty | FAIL | FAIL | FAIL - file:outputs/setup_top10.rpt: missing |
| TA-04 | alt1 | PASS | PASS | PASS (10 checks) |
| TA-04 | alt2 | PASS | PASS | PASS (10 checks) |
| TA-04 | alt3 | PASS | PASS | PASS (10 checks) |
| TA-04 | neg1 | FAIL | FAIL | FAIL - worst_endpoints: not among the 10 worst: _705_, resp_msg[13]; missing worst endpoints: _702_, _704_; slacks_match |
| TA-04 | neg2 | FAIL | FAIL | FAIL - path_type: found Path Type ['min'], expected max; worst_endpoints: not among the 10 worst: _672_, _673_, _674_, _ |
| TA-04 | neg3 | FAIL | FAIL | FAIL - one_path_per_endpoint: repeated endpoints ['resp_msg[15]']; worst_endpoints: missing worst endpoints: _691_, _694 |
| TA-04 | neg4 | FAIL | FAIL | FAIL - slacks_match_ground_truth: resp_msg[15]: -0.0500 vs -0.04288; resp_msg[14]: -0.0455 vs -0.01969; _706_: -0.0410 v |
| TA-04 | neg5 | FAIL | FAIL | FAIL - design_unchanged: cell masters changed; worst_endpoints: not among the 10 worst: _692_; missing worst endpoints:  |
| TA-04 | neg6 | FAIL | FAIL | FAIL - path_count: 0 paths reported, 10 required |
| TA-05 | reference | PASS | PASS | PASS (6 checks) |
| TA-05 | empty | FAIL | FAIL | FAIL - file:outputs/wns_tns.txt: missing |
| TA-05 | alt1 | PASS | PASS | PASS (6 checks) |
| TA-05 | alt2 | PASS | PASS | PASS (6 checks) |
| TA-05 | alt3 | PASS | PASS | PASS (6 checks) |
| TA-05 | neg1 | FAIL | FAIL | FAIL - WNS: -0.0518 vs ground truth -0.05936 (tol 0.0001, >= 4 decimals); TNS: -0.6325 vs ground truth -0.88292 (tol 0.0 |
| TA-05 | neg2 | FAIL | FAIL | FAIL - WNS: -0.0602 vs ground truth -0.05936 (tol 0.0001, >= 4 decimals); TNS: -1.1392 vs ground truth -0.88292 (tol 0.0 |
| TA-05 | neg3 | FAIL | FAIL | FAIL - WNS: -0.0377 vs ground truth -0.05936 (tol 0.0001, >= 4 decimals); TNS: -0.0772 vs ground truth -0.88292 (tol 0.0 |
| TA-05 | neg4 | FAIL | FAIL | FAIL - WNS: -0.06 vs ground truth -0.05936 (tol 0.0001, >= 4 decimals); TNS: -0.88 vs ground truth -0.88292 (tol 0.003,  |
| TA-05 | neg5 | FAIL | FAIL | FAIL - layout: 2 non-empty lines, 1 required |
| TA-06 | reference | PASS | PASS | PASS (6 checks) |
| TA-06 | empty | FAIL | FAIL | FAIL - file:outputs/max_transition_violations.rpt: missing; file:outputs/max_capacitance_violations.rpt: missing |
| TA-06 | alt1 | PASS | PASS | PASS (6 checks) |
| TA-06 | alt2 | PASS | PASS | PASS (6 checks) |
| TA-06 | alt3 | PASS | PASS | PASS (6 checks) |
| TA-06 | alt4 | PASS | PASS | PASS (6 checks) |
| TA-06 | neg1 | FAIL | FAIL | FAIL - max_capacitance_violators: 389 pins listed, 27 violate; not violating _345_/ZN, _347_/ZN, _349_/ZN, _350_/ZN, _35 |
| TA-06 | neg2 | FAIL | FAIL | FAIL - max_transition_violators: 42 pins listed, 76 violate; missing _581_/ZN, _583_/A2, _585_/ZN, _587_/A1, _590_/A2, _ |
| TA-06 | neg3 | FAIL | FAIL | FAIL - design_unchanged: cell masters changed; file:outputs/max_transition_violations.rpt: empty; max_capacitance_violat |
| TA-06 | neg4 | FAIL | FAIL | FAIL - max_transition_violators: 100 pins listed, 76 violate; not violating _348_/ZN, _393_/ZN, _394_/ZN, _396_/ZN, _428 |
| TA-06 | neg5 | FAIL | FAIL | FAIL - file:outputs/max_transition_violations.rpt: empty |
| TA-06 | neg6 | FAIL | FAIL | FAIL - file:outputs/max_transition_violations.rpt: empty; file:outputs/max_capacitance_violations.rpt: empty |
| TA-07 | reference | PASS | PASS | PASS (9 checks) |
| TA-07 | empty | FAIL | FAIL | FAIL - spef:outputs/gcd.spef: missing; file:outputs/signoff_summary.txt: missing |
| TA-07 | alt1 | PASS | PASS | PASS (9 checks) |
| TA-07 | alt2 | PASS | PASS | PASS (9 checks) |
| TA-07 | alt3 | PASS | PASS | PASS (9 checks) |
| TA-07 | neg1 | FAIL | FAIL | FAIL - worst_setup_slack: -0.0377 vs ground truth -0.05356 (tol 0.0001, >= 4 decimals); total_negative_setup_slack: -0.0 |
| TA-07 | neg2 | FAIL | FAIL | FAIL - worst_setup_slack: -0.0594 vs ground truth -0.05356 (tol 0.0001, >= 4 decimals); total_negative_setup_slack: -0.8 |
| TA-07 | neg3 | FAIL | FAIL | FAIL - worst_hold_slack: 0.0000 vs ground truth 0.05120 (tol 0.0001, >= 4 decimals) |
| TA-07 | neg4 | FAIL | FAIL | FAIL - spef:outputs/gcd.spef: missing |
| TA-07 | neg5 | FAIL | FAIL | FAIL - setup_violating_endpoints: 965 vs ground truth 40 |
| TA-08 | reference | PASS | PASS | PASS (7 checks) |
| TA-08 | empty | FAIL | FAIL | FAIL - file:outputs/slow_corner.txt: missing |
| TA-08 | alt1 | PASS | PASS | PASS (7 checks) |
| TA-08 | alt2 | PASS | PASS | PASS (7 checks) |
| TA-08 | alt3 | PASS | PASS | PASS (7 checks) |
| TA-08 | alt4 | PASS | PASS | PASS (7 checks) |
| TA-08 | alt5 | PASS | PASS | PASS (7 checks) |
| TA-08 | neg1 | FAIL | FAIL | FAIL - min_clock_period: 1.70 vs ground truth 1.70360 (tol 0.0002, >= 4 decimals) |
| TA-08 | neg2 | FAIL | FAIL | FAIL - worst_setup_slack: -1.2333 vs ground truth -1.21860 (tol 0.0001, >= 4 decimals); total_negative_setup_slack: -50. |
| TA-08 | neg3 | FAIL | FAIL | FAIL - worst_setup_slack: -1.1214 vs ground truth -1.21860 (tol 0.0001, >= 4 decimals); total_negative_setup_slack: -44. |
| TA-08 | neg4 | FAIL | FAIL | FAIL - min_clock_period: -0.7336 vs ground truth 1.70360 (tol 0.0002, >= 4 decimals) |
| TA-08 | neg5 | FAIL | FAIL | FAIL - worst_setup_slack: -0.0429 vs ground truth -1.21860 (tol 0.0001, >= 4 decimals); total_negative_setup_slack: -0.1 |
| TA-08 | neg6 | FAIL | FAIL | FAIL - worst_setup_slack: -0.0429 vs ground truth -1.21860 (tol 0.0001, >= 4 decimals); total_negative_setup_slack: -0.1 |
| DEV-CT-01 | reference | PASS | PASS | PASS (7 checks) |
| DEV-CT-01 | empty | FAIL | FAIL | FAIL - clock_tree_built: 35/35 register clock pins reached from the clock port, 35 driven directly by the port, 0 clock- |
| DEV-CT-01 | alt1 | PASS | PASS | PASS (7 checks) |
| DEV-CT-01 | alt2 | PASS | PASS | PASS (7 checks) |
| DEV-CT-01 | alt3 | PASS | PASS | PASS (7 checks) |
| DEV-CT-01 | neg1 | FAIL | FAIL | FAIL - placement_legal: check_placement legal=False |
| DEV-CT-01 | neg2 | FAIL | FAIL | FAIL - clock_buffer_masters: root ['BUF_X4'], tree ['BUF_X4'] (expected root ['BUF_X2'], tree ['BUF_X2']); masters used  |
| DEV-CT-01 | neg3 | FAIL | FAIL | FAIL - placement_legal: check_placement legal=False |
| DEV-CT-01 | neg4 | FAIL | FAIL | FAIL - clock_buffer_masters: root ['BUF_X4'], tree ['BUF_X4'] (expected root ['BUF_X2'], tree ['BUF_X2']); masters used  |
| DEV-EX-01 | reference | PASS | PASS | PASS (6 checks) |
| DEV-EX-01 | empty | FAIL | FAIL | FAIL - rows_created: 0 rows; core_utilization: value unavailable (target 0.35); die_and_core_defined: die or core area m |
| DEV-EX-01 | alt1 | PASS | PASS | PASS (6 checks) |
| DEV-EX-01 | neg1 | FAIL | FAIL | FAIL - core_utilization: value 0.525551, target 0.35 +/- 0.03 |
| DEV-EX-01 | neg2 | FAIL | FAIL | FAIL - routing_tracks_all_layers: track grids on [] |
| DEV-FP-01 | reference | PASS | PASS | PASS (8 checks) |
| DEV-FP-01 | empty | FAIL | FAIL | FAIL - all_pins_placed: 0/54 placed; unplaced e.g. ['clk', 'req_msg[0]', 'req_msg[10]', 'req_msg[11]']; pins_on_die_boun |
| DEV-FP-01 | alt1 | PASS | PASS | PASS (8 checks) |
| DEV-FP-01 | alt2 | PASS | PASS | PASS (8 checks) |
| DEV-FP-01 | neg1 | FAIL | FAIL | FAIL - outputs_on_right: 0/18 output pins on the right edge; e.g. ['req_rdy', 'resp_msg[0]', 'resp_msg[10]', 'resp_msg[1 |
| DEV-FP-01 | neg2 | FAIL | FAIL | FAIL - inputs_on_left: 0/36 input pins on the left edge; e.g. ['clk', 'req_msg[0]', 'req_msg[10]', 'req_msg[11]']; outpu |
| DEV-FP-01 | neg3 | FAIL | FAIL | FAIL - inputs_on_left: 4/36 input pins on the left edge; e.g. ['req_msg[0]', 'req_msg[10]', 'req_msg[11]', 'req_msg[12]' |
| DEV-IN-01 | reference | PASS | PASS | PASS (6 checks) |
| DEV-IN-01 | empty | FAIL | FAIL | FAIL - file:outputs/unloaded_nets.txt: missing |
| DEV-IN-01 | alt1 | PASS | PASS | PASS (6 checks) |
| DEV-IN-01 | alt2 | PASS | PASS | PASS (6 checks) |
| DEV-IN-01 | neg1 | FAIL | FAIL | FAIL - net_set: 35 nets listed, 34 expected; missing [], unexpected ['_003_'] |
| DEV-IN-01 | neg2 | FAIL | FAIL | FAIL - file:outputs/unloaded_nets.txt: empty |
| DEV-IN-01 | neg3 | FAIL | FAIL | FAIL - driver_pins: wrong: _311_ _673_ (is _673_/QN), _312_ _674_ (is _674_/QN), _313_ _675_ (is _675_/QN), _314_ _676_  |
| DEV-OP-01 | reference | PASS | PASS | PASS (7 checks) |
| DEV-OP-01 | empty | FAIL | FAIL | FAIL - max_fanout: largest non-clock fanout 40.0 on net req_rdy (start 40.0, limit 10) |
| DEV-OP-01 | alt1 | PASS | PASS | PASS (7 checks) |
| DEV-OP-01 | alt2 | PASS | PASS | PASS (7 checks) |
| DEV-OP-01 | alt3 | PASS | PASS | PASS (7 checks) |
| DEV-OP-01 | alt4 | PASS | PASS | PASS (7 checks) |
| DEV-OP-01 | neg1 | FAIL | FAIL | FAIL - max_fanout: largest non-clock fanout 16.0 on net net3 (start 40.0, limit 10) |
| DEV-OP-01 | neg2 | FAIL | FAIL | FAIL - max_fanout: largest non-clock fanout 40.0 on net req_rdy (start 40.0, limit 10) |
| DEV-OP-01 | neg3 | FAIL | FAIL | FAIL - placement_legal: check_placement legal=False |
| DEV-OP-01 | neg4 | FAIL | FAIL | FAIL - max_fanout: largest non-clock fanout 40.0 on net req_rdy (start 40.0, limit 10) |
| DEV-OP-01 | neg5 | FAIL | FAIL | FAIL - clock_tree_unchanged: clock network changed at 36 points (e.g. _672_/CK: PORT:clk -> clkbuf_2_3__f_clk:BUF_X4>clk |
| DEV-OP-01 | neg6 | FAIL | FAIL | FAIL - logic_preserved: 15 new logic cells are neither buffers nor gate clones (e.g. fo_inv_0 (INV_X2), fo_inv_1 (INV_X2 |
| DEV-PL-01 | reference | PASS | PASS | PASS (7 checks) |
| DEV-PL-01 | empty | FAIL | FAIL | FAIL - placement_legal: check_placement legal=False; row_orientation: 346 cells off-row or with an orientation not match |
| DEV-PL-01 | alt1 | PASS | PASS | PASS (7 checks) |
| DEV-PL-01 | alt2 | PASS | PASS | PASS (7 checks) |
| DEV-PL-01 | alt3 | PASS | PASS | PASS (7 checks) |
| DEV-PL-01 | neg1 | FAIL | FAIL | FAIL - gap_around_masters: 35 'DFF_*' cells: smallest left gap 0.00, right gap 0.00 sites (>= 3) |
| DEV-PL-01 | neg2 | FAIL | FAIL | FAIL - gap_around_masters: 35 'DFF_*' cells: smallest left gap 0.00, right gap 3.00 sites (>= 3) |
| DEV-PL-01 | neg3 | FAIL | FAIL | FAIL - gap_around_masters: 35 'DFF_*' cells: smallest left gap 2.00, right gap 2.00 sites (>= 3) |
| DEV-PL-01 | neg4 | FAIL | FAIL | FAIL - gap_around_masters: 35 'DFF_*' cells: smallest left gap 2.00, right gap 2.00 sites (>= 3) |
| DEV-RT-01 | reference | PASS | PASS | PASS (6 checks) |
| DEV-RT-01 | empty | FAIL | FAIL | FAIL - all_nets_detail_routed: 0/413 routable nets have detailed routing (413 in the starting state); report:outputs/dr_ |
| DEV-RT-01 | alt1 | PASS | PASS | PASS (6 checks) |
| DEV-RT-01 | alt2 | PASS | PASS | PASS (6 checks) |
| DEV-RT-01 | neg1 | FAIL | FAIL | FAIL - routing_layer_range: wires outside metal2-metal10: metal1 27.9 um |
| DEV-RT-01 | neg2 | FAIL | FAIL | FAIL - total_detailed_route_wirelength: value 7925.4, target 5753.39 +/- 28.8 |
| DEV-RT-01 | neg3 | FAIL | FAIL | FAIL - routing_layer_range: wires outside metal2-metal10: metal1 27.9 um |
| DEV-RT-01 | neg4 | FAIL | FAIL | FAIL - total_detailed_route_wirelength: value 1.15068e+07, target 5753.39 +/- 28.8 |
| DEV-TA-01 | reference | PASS | PASS | PASS (6 checks) |
| DEV-TA-01 | empty | FAIL | FAIL | FAIL - file:outputs/period_0p40.txt: missing |
| DEV-TA-01 | alt1 | PASS | PASS | PASS (6 checks) |
| DEV-TA-01 | alt2 | PASS | PASS | PASS (6 checks) |
| DEV-TA-01 | neg1 | FAIL | FAIL | FAIL - worst_setup_slack: -0.0111 vs ground truth -0.09606 (tol 0.0001, >= 4 decimals); setup_violating_endpoints: 1 vs  |
| DEV-TA-01 | neg2 | FAIL | FAIL | FAIL - worst_setup_slack: -0.0791 vs ground truth -0.09606 (tol 0.0001, >= 4 decimals); setup_violating_endpoints: 39 vs |
| DEV-TA-01 | neg3 | FAIL | FAIL | FAIL - worst_setup_slack: -0.0692 vs ground truth -0.09606 (tol 0.0001, >= 4 decimals); setup_violating_endpoints: 32 vs |
| DEV-TA-01 | neg4 | FAIL | FAIL | FAIL - worst_setup_slack: -0.0692 vs ground truth -0.09606 (tol 0.0001, >= 4 decimals); setup_violating_endpoints: 32 vs |
| DEV-TA-01 | neg5 | FAIL | FAIL | FAIL - worst_setup_slack: -0.1279 vs ground truth -0.09606 (tol 0.0001, >= 4 decimals); setup_violating_endpoints: 43 vs |
