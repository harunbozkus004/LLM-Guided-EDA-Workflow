# Re-reads the netlist "to be safe": this replaces the post-CTS design with the synthesized one.
read_verilog design/gcd.v
link_design gcd
write_verilog outputs/gcd_netlist.v
