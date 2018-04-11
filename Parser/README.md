# Packet Parser
C++ description of P4-compatible packet parser.

The generated code implements an pipelined packet parser based on a P4 description.

## Usage

+ C++ files generation
```console
~$ cd scripts
~$ ./gen_parser_pipe.sh <name of you P4 file> <pipeline bus size in bits>
~$ cd ..
```

+ FPGA synthesis
```console
~$ cd synth
~$ vivado_hls -f script.tcl
~$ cd ..
```