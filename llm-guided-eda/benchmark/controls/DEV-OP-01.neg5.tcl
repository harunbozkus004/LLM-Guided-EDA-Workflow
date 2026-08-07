# Clock net touched: the clock net (fanout 35) is buffered too, by building a clock tree.
set_max_fanout 10 [current_design]
estimate_parasitics -placement
repair_design
clock_tree_synthesis -root_buf BUF_X4 -buf_list BUF_X4 -sink_clustering_enable
detailed_placement
