# Alternative: report written through the STA redirection API.
estimate_parasitics -placement
sta::redirect_file_begin outputs/ct03_clock_skew.rpt
report_clock_skew -setup -clock core_clock -digits 4
sta::redirect_file_end
