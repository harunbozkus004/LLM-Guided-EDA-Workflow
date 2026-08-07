# Alternative: resize the root through the database API, found by name.
clock_tree_synthesis -buf_list BUF_X2
set root [[ord::get_db_block] findInst clkbuf_0_clk]
$root swapMaster [[ord::get_db] findMaster BUF_X8]
detailed_placement
