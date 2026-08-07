# Alternative: defensive ripup of any existing tap/endcap cells, then the standard tapcell call.
tapcell_ripup -tap_prefix TAP_ -endcap_prefix PHY_
tapcell -distance 20 -tapcell_master TAPCELL_X1 -endcap_master TAPCELL_X1 -tap_prefix TAP_ -endcap_prefix PHY_
