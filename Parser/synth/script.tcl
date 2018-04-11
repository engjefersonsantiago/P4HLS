open_project -reset synth
set_top HeaderAnalysisTop
add_files ../src/Header.hpp -cflags "-std=c++0x"
add_files ../src/Parser.cpp -cflags "-std=c++0x"
add_files ../src/Parser.hpp -cflags "-std=c++0x"
add_files ../src/defined_types.h -cflags "-std=c++0x"
add_files ../src/parser_header_template.hpp -cflags "-std=c++0x"
add_files ../src/pktBasics.hpp -cflags "-std=c++0x"
#add_files -tb ../src/Parser_tb.cpp -cflags "-std=c++0x"
open_solution "synthesis"
set_part {xc7vx690tffg1761-2}
create_clock -period 3.2 -name default
#source "./synth/solution1/directives.tcl"
#csim_design
csynth_design
#cosim_design -trace_level all
export_design -flow syn -rtl vhdl -format ip_catalog
exit
