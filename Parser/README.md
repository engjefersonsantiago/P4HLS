# Packet Parser
C++ description of P4-compatible packet parser.

The generated code implements an pipelined packet parser based on a P4 description.

## Full description

For a more complete description, please refer to the related paper presented at [FPGA'18](https://dl.acm.org/citation.cfm?id=3174270).

To cite the paper please use:
```
@inproceedings{SantiagodaSilva:2018:PHS:3174243.3174270,
 author = {Santiago da Silva, Jeferson and Boyer, Fran\c{c}ois-Raymond and Langlois, J.M. Pierre},
 title = {P4-Compatible High-Level Synthesis of Low Latency 100 Gb/s Streaming Packet Parsers in FPGAs},
 booktitle = {Proceedings of the 2018 ACM/SIGDA International Symposium on Field-Programmable Gate Arrays},
 series = {FPGA '18},
 year = {2018},
 isbn = {978-1-4503-5614-5},
 location = {Monterey, CALIFORNIA, USA},
 pages = {147--152},
 numpages = {6},
 url = {http://doi.acm.org/10.1145/3174243.3174270},
 doi = {10.1145/3174243.3174270},
 acmid = {3174270},
 publisher = {ACM},
 address = {New York, NY, USA},
 keywords = {fpga, hls, p4, packet parsers, programmable networks},
} 
```

## Usage

+ C++ files generation
```console
~$ cd scripts
~$ ./gen_parser_pipe.sh <name of your P4 file> <pipeline bus size in bits>
~$ cd ..
```

+ FPGA synthesis
```console
~$ cd synth
~$ vivado_hls -f script.tcl
~$ cd ..
```
