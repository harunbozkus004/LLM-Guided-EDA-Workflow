# Alternative: sink clustering (three-level tree); every clk-port load is upsized through the
# database API, then legalized.
clock_tree_synthesis -root_buf BUF_X2 -buf_list BUF_X2 -sink_clustering_enable -sink_clustering_size 6
set block [ord::get_db_block]
foreach it [[[$block findBTerm clk] getNet] getITerms] {
  if {[$it isInputSignal]} { [$it getInst] swapMaster [[ord::get_db] findMaster BUF_X8] }
}
detailed_placement
check_placement
