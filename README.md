# P4HLS
C++ description of P4-compatible HLS modules.

This repository implements P4-compatible modules for HLS-driven FPGA synthesis mainly relying in C++11 high-level descriptions.

## Requirements
+ Xilinx Vivado Design Suite V2017.4 (Vivado HLS is required)
+ Python 2.7
+ [p4c-bm compiler](https://github.com/engjefersonsantiago/p4c-bm)

## Specific Packages
```console
~$ sudo apt-get install libgnome2-bin python-dev graphviz libgraphviz-dev pkg-config
~$ sudo pip install pip networkx
~$ sudo pip install pygraphviz --install-option="--include-path=/usr/include/graphviz" --install-option="--library-path=/usr/lib/graphviz/" --upgrade --force-reinstall 
```

## Packet Parser
For a detailed description please refer to the [Parser](https://github.com/engjefersonsantiago/P4HLS/tree/master/Parser) folder.
