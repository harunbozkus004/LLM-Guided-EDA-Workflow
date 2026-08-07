# Retrieval evaluation

40 labeled questions (knowledge_base/retrieval_eval.json); index of 1632 chunks built 2026-07-08T09:37:04+00:00, embedding model BAAI/bge-small-en-v1.5.

| mode | recall@1 | recall@3 | recall@6 | mrr@10 | command_hit@6 | mean latency (ms) |
|---|---:|---:|---:|---:|---:|---:|
| vector | 0.450 | 0.700 | 0.875 | 0.608 | 0.975 | 13 |
| bm25 | 0.400 | 0.675 | 0.800 | 0.563 | 0.900 | 1 |
| hybrid | 0.475 | 0.800 | 0.925 | 0.650 | 1.000 | 14 |

Hybrid = reciprocal rank fusion (k=60) of the top 8 vector and top 8 BM25 hits. Every mode deduplicates chunks with the same source + section (each ranker's list holds distinct sections; hybrid fuses per section and shows the section's best chunk).

Definitions: **relevant**: chunk source matches a labeled source file AND the chunk text/section mentions a labeled command (whole word); **recall@k**: fraction of questions with >= 1 relevant chunk among the top k (hit rate); **mrr@10**: mean reciprocal rank of the first relevant chunk in the top 10 (0 when none); **command_hit@6**: secondary: fraction of questions whose top 6 contain a chunk from ANY source (documentation, example or flow script) naming a labeled command

Note: The questions were written before any retrieval result was seen. There is no separate development set: the same 40 questions were used to check three design changes (Porter stemming in BM25, per-ranker source+section deduplication before fusion, tool names in README titles), so the numbers are slightly optimistic. Relevance counts only the labeled primary documentation; usage examples are credited by command_hit@6 only.

## Per question (rank of the first relevant chunk, '-' = not in top 10)

| id | question | vector | bm25 | hybrid |
|---|---|---:|---:|---:|
| q01 | How do I legalize the placement after global placement? | 8 | 4 | 4 |
| q02 | How do I set the target placement density for global placement? | 4 | 7 | 6 |
| q03 | Place the macros with a halo around each macro and channel spacing between them | 1 | 1 | 1 |
| q04 | Create the floorplan from a target core utilization and aspect ratio | 1 | 2 | 1 |
| q05 | How do I generate the routing tracks for each metal layer? | 7 | 9 | 3 |
| q06 | Place the I/O pins on a given horizontal and vertical metal layer | 1 | 5 | 1 |
| q07 | Restrict a group of pins to the top edge of the die | 2 | 1 | 1 |
| q08 | Insert tap cells and endcaps into the standard cell rows | 3 | 2 | 2 |
| q09 | Connect the VDD and VSS pins of all standard cells to the global power and ground nets | 2 | - | 6 |
| q10 | Add power straps on metal4 with a given width and pitch to the power grid | 1 | 1 | 1 |
| q11 | Set the resistance and capacitance per unit length of signal and clock wires used for parasitic estimation | 1 | 1 | 1 |
| q12 | estimate wire parasitics after placement for timing analysis | 1 | 1 | 1 |
| q13 | Fix max slew, max capacitance and max fanout violations | - | - | - |
| q14 | How can I fix hold time violations after clock tree synthesis? | 4 | 4 | 3 |
| q15 | Exclude some library cells from being used by the optimizer | 1 | 1 | 1 |
| q16 | Remove the buffers that synthesis inserted in the netlist | 1 | 1 | 1 |
| q17 | Tie off constant nets with tie-high and tie-low cells placed close to their loads | 4 | 1 | 2 |
| q18 | Build the clock tree with a specific root buffer and list of clock buffers, with sink clustering | 1 | 2 | 1 |
| q19 | Report the number of clock buffers and clock nets created by CTS | 2 | 2 | 2 |
| q20 | Fill the empty space in the placement rows with filler cells | 1 | 1 | 1 |
| q21 | check_placement verbose report of illegally placed cells | 1 | 1 | 1 |
| q22 | Leave extra space on the left and right of every cell during legalization to help routability | - | 1 | 4 |
| q23 | Run global routing and save the route guides to a file | 2 | 1 | 3 |
| q24 | Which metal layers can the global router use for signal nets and for clock nets? | 1 | 3 | 1 |
| q25 | Reduce the routing capacity of a layer by a percentage to relieve congestion | 1 | 2 | 1 |
| q26 | detailed_route options to write the DRC violation report and limit the top routing layer | 2 | 3 | 1 |
| q27 | Check the routed design for antenna rule violations | 2 | 2 | 2 |
| q28 | Fix antenna violations by inserting diodes after global routing | 1 | 1 | 1 |
| q29 | Extract RC parasitics of the routed design with an extraction rules file and write a SPEF file | 3 | 9 | 5 |
| q30 | Report the 10 worst setup timing paths instead of only the single worst one | 3 | 8 | 2 |
| q31 | Report the worst negative slack and the total negative slack of the design | 1 | 5 | 2 |
| q32 | Define a clock with a 10 ns period on the clk port | 5 | 2 | 3 |
| q33 | Constrain the arrival time of input ports relative to a clock | 1 | 1 | 1 |
| q34 | Use propagated clock latency instead of ideal clocks after the clock tree is built | 1 | 3 | 2 |
| q35 | How do I report power broken down into internal, switching and leakage power? | 2 | 1 | 2 |
| q36 | List all max slew and max capacitance limit violations | - | 5 | - |
| q37 | Make timing paths between two asynchronous clock domains not be analyzed | 6 | 1 | 1 |
| q38 | Compute the IR drop of the VDD power network | 4 | - | 7 |
| q39 | Get a list of all the flip-flop instances in the design | 5 | 10 | 2 |
| q40 | Write out the final gate-level netlist as Verilog without the filler cells | 1 | 3 | 1 |
