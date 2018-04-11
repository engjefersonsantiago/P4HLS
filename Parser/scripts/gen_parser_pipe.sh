#!/bin/sh
die () {
    echo >&2 "$@"
    exit 1
}

[ "$#" -eq 2 ] || die "2 arguments required, $# provided. First: p4 file name, second: bus size in bits"
set -m
p4c-bmv2 $1.p4 --json $1.json --p4-v1.1 
if [ $? -ne 0 ]; then
echo "P4 compilation failed"
exit 1
fi
python generate_header_parser.py headers_and_parser.json $2 16
gnome-open full_graph.pdf
gnome-open simpl_graph.pdf
echo "Copying generated files to src directory"
cp parser_header_template.hpp ../src/
cp Parser.hpp ../src/
cp Parser.cpp ../src/
