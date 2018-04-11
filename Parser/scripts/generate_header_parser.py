###############################################################################
# Packet Parser generator: code generation for a packet parser                #
# Jeferson Santiago da Silva (eng.jefersonsantiago@gmail.com)                 #
###############################################################################

import json
import string
import sys
import math
import copy
import re
from pygraphviz import *
import networkx as nx
import matplotlib.pyplot as plt
from networkx.drawing.nx_agraph import graphviz_layout, to_agraph

HEADER_TYPES_STR = "header_types"
HEADER_INST_STR = "headers"
PARSER_INST_STR = "parsers"

def recur_search (exp_dict):
    expr_str = ""
    if exp_dict["type"] == "expression":
        expr_str = expr_str + "(" + (str(recur_search(exp_dict["value"]["left"])) + str(exp_dict["value"]["op"]) + str(recur_search(exp_dict["value"]["right"]))) + ")"
    else:
        if exp_dict["type"] != "local":
            expr_str = expr_str + str(exp_dict["value"])
        else:
            expr_str = expr_str + "field[" + str(exp_dict["value"]) + "]"    #expr_val is the variable name used in the header layout struct

    return expr_str

def draw_graph(Graph, file):
        G = nx.DiGraph(Graph, directed=True)
        G.graph['graph']={'rankdir':'TD'}
        G.graph['node']={'shape':'box'}
        G.graph['edges']={'arrowsize':'4.0'}
        A = to_agraph(G)
        A.layout('dot')
        A.draw(file)

def transf_graph(headers_list):
    edges = []
    nodes = []
    for headers_t in headers_list:
        nodes.append(headers_t["header_name"])
        for nstates in headers_t["next_state"]:
            edges.append((headers_t["header_name"], nstates))

    full_graph = AGraph(directed=True, acyclic=True)
    full_graph.add_nodes_from(nodes)
    full_graph.add_edges_from(edges)
    reduced_graph = full_graph.tred(copy=True)
    full_graph.write('full_graph.dot')
    reduced_graph.write('reduced_graph.dot')
    
    G = nx.DiGraph()
    G.add_nodes_from(reduced_graph.nodes())
    G.add_edges_from(reduced_graph.edges())
    try:
    	longest_path = nx.dag_longest_path(G)
    except nx.exception.NetworkXUnfeasible: # There's a loop!
     	print("The graph has a cycle")
    
    nodes = reduced_graph.nodes()
    edges = reduced_graph.edges()
    
    # [Graph_Level, Dummy_Insertion]
    nodes_dict = {}
    
    for i in nodes:
    	if i in longest_path:
    		nodes_dict[i] = [None]*3
    
    	for j in range(len(longest_path)):
    		if longest_path[j] == i:
    			nodes_dict[i][0] = j
    			nodes_dict[i][1] = False
    
    for i in nodes:
    	if i in longest_path:
    		continue
    
    	nodes_dict[i] = [None]*3
    	predecessors = reduced_graph.predecessors(i)
    	max_val = 0
    	
    	for pred in predecessors:
    		for nnodes in nodes_dict:
    			if nnodes == pred:
    				if nodes_dict[nnodes][0] >= max_val:
    					max_val = nodes_dict[nnodes][0] 
    
    	nodes_dict[i][0] = max_val + 1
    	nodes_dict[i][1] = False
    
    for i in nodes:
    	nodes_dict[i][2] = False
    	successors = reduced_graph.successors(i)
    	succ_levels = []
    	for succ in successors:
    		for nnodes in nodes_dict:
    			if nnodes == succ:
    				if nodes_dict[nnodes][0] != nodes_dict[i][0] + 1:
    					nodes_dict[i][1] = True
    					break
    
    nodes_dict.pop('end')
    
    #for nnodes in nodes_dict:
    	#print nnodes
    	#print nodes_dict[nnodes]
    
    nodes_list = [] 
    nodes_levels = []
    for i in nodes_dict:
    	nodes_list.append([i, nodes_dict[i]])
    	nodes_levels.append(nodes_dict[i][0])
    
    #print nodes_list
    #print nodes_levels
    nodes_levels.sort()
    #print nodes_levels
    nodes_list2 = [None]*len(nodes_list)
    int_num = 0
    
    for i in range(len(nodes_levels)):
    	for j in nodes_list:
    		if j[1][0] == nodes_levels[i] and not j[1][2]:
    			nodes_list2[i] = j
    			j[1][2]=True
    			break
    
    #for i in nodes_list2:
    	#print i
 
    draw_graph(full_graph, 'full_graph.pdf')

    return nodes_list2, nodes_levels 

##################################################33
def json_parser(json_file):
	with open(json_file) as data_file:
		data = json.load(data_file)

	#Retrieving relevant json arrays from json descritpion
	for json_array in data:
		if json_array == HEADER_TYPES_STR:
			header_types = data[json_array]
		if json_array == HEADER_INST_STR:
			headers_inst = data[json_array]
		if json_array == PARSER_INST_STR:
			parser_inst = data[json_array]

	#Header declaration analisys
	headers_list = []
	for headers in header_types:
		header_dict = {}
		header_dict["num_fields"] = len(headers["fields"])
		header_dict["fields"] = [None]*header_dict["num_fields"]
                field_offset = 0
                for field in range(header_dict["num_fields"]):
                    header_dict["fields"][field] = [None]*3
	            header_dict["fields"][field][0] = headers["fields"][field][0]
	            header_dict["fields"][field][1] = field_offset
                    if field == header_dict["num_fields"] - 1 and headers["max_length"] != None:
                        header_dict["fields"][field][2] = 8*headers["max_length"] - field_offset
                        field_offset = 8*headers["max_length"]
                        header_dict["var_size_header"] = True
                    else:
                        header_dict["fields"][field][2] = headers["fields"][field][1]
                        field_offset+=int(headers["fields"][field][1])
                        header_dict["var_size_header"] = False

                header_dict["header_length_lookup_array"] = []
                header_dict["header_length_field"] = ""
                header_dict["header_length_position"] = 0
		header_dict["header_length_size"] = 1
		header_dict["header_length_expression"] = ""
                expr = headers["length_exp"] 
                exp_str = ""
                exp_field = 0
                if expr != None:
                    if expr["type"] == "expression":     
                        if expr["value"]["op"] == "-":   # only interested in parsing inside the '-' expression
                            exp_str = recur_search(expr["value"]["left"]) 
                            exp_re = r'field\[(\w+)\]'
                            header_field_exp = re.findall(exp_re, exp_str)
                            header_dict["header_length_field"] = str(header_dict["fields"][int(header_field_exp[0])][0]) 
                            header_dict["header_length_expression"] = re.sub(exp_re, header_dict["header_length_field"], exp_str)
                            header_dict["header_length_position"] = header_dict["fields"][int(header_field_exp[0])][1] 
                            header_dict["header_length_size"] = header_dict["fields"][int(header_field_exp[0])][2] 
                    print "Found a variable size header: " + headers["name"] + ". Header length expression: " + header_dict["header_length_expression"]
                header_dict["parser_state"] = ""
		header_dict["parser_state_id"] = 0
		header_dict["next_state"] = []
		header_dict["next_state_id"] = []
		header_dict["previous_state"] = []
		header_dict["previous_state_id"] = []
		header_dict["previous_state_both"] = []
		header_dict["header_size"] = field_offset/8
		header_dict["header_size_bits"] = field_offset
		header_dict["num_fields"] = len(headers["fields"])
		header_dict["extr_mask"] = ((1 << header_dict["header_size_bits"]) - 1)
		header_dict["transition_keys"] = []
		header_dict["key_name"] = ""
		header_dict["key_position"] = 0
		header_dict["key_size"] = 1			# Workaround for final states
		header_dict["key_type"] = "ap_uint<1>"		# Workaround for final states
		header_dict["key_number"] = 0

		header_dict["last_header"] = True
		header_dict["first_header"] = False
		header_dict["header_type_name"] = headers["name"]
		header_dict["header_name"] = "" #from instantiation
		header_dict["header_id"] = headers["id"]
		header_dict["metadata"] = False

                if header_dict["var_size_header"]:
                    exp_str = header_dict["header_length_expression"] 
                    fx = re.sub(header_dict["header_length_field"], "x", exp_str) 
                    f = lambda x: eval(fx)
                    for i in range(header_dict["header_size_bits"]):
                        res = f(i)
                        if res >  header_dict["header_size_bits"]:
                            break
                        else:
                            header_dict["header_length_lookup_array"].append(res)
                    #print(header_dict["header_length_lookup_array"])
                else:
                    header_dict["header_length_lookup_array"].append(1)
                header_dict["header_length_larray_size"] = len(header_dict["header_length_lookup_array"])
                last_len_elem = header_dict["header_length_lookup_array"][header_dict["header_length_larray_size"] - 1] 
                #print (last_len_elem)
                len_bit_size = 0 
                if last_len_elem % 2:
                    if last_len_elem == 1:
                        len_bit_size = 1
                    else:
                        len_bit_size = int(math.ceil(math.log(last_len_elem, 2)))
                else:
                    len_bit_size = int(math.ceil(math.log(last_len_elem + 1, 2)))
                header_dict["len_bit_size"] = len_bit_size

                headers_list.append(header_dict)

	#Header instantiation analisys
	for header_i in headers_inst:
		for headers_t in headers_list:
			if headers_t["header_type_name"] == header_i["header_type"]:
				print "Found an instantiation for the header type " + header_i["header_type"] \
						+ " with the name " + header_i["name"]
				headers_t["header_name"] = header_i["name"]
				if headers_t["header_id"] != header_i["id"]:
					headers_t["header_id"] = header_i["id"]
					print "Header identifier different in the declaration and instantiation." \
							+ " Using the instantiation value"
				if header_i["metadata"]:
					print "Header " + header_i["name"] + " is a metadata instance. Removing from header list"
					headers_t["metadata"] = True
					headers_list.remove(headers_t)
				break

	#Header parser analisys
	for parser_i in parser_inst:
		parser_ini_state = parser_i["init_state"]
		parser_name = parser_i["name"]
		parser_id = parser_i["id"]
		for states in parser_i["parse_states"]:
			# Linking parser state and header name
			for ops in states["parser_ops"]:
				for ops_params in ops["parameters"]:
					for headers_t in headers_list:
						if ops_params["value"] == headers_t["header_name"]:
							headers_t["parser_state"] = states["name"]
							headers_t["parser_state_id"] = states["id"]
							print "Linking header " + headers_t["header_name"] + " to parser state " \
									+ headers_t["parser_state"] + " with ID " + str(headers_t["parser_state_id"])
			# Retriving transition key
			for keys in states["transition_key"]:
				for headers_t in headers_list:
					if headers_t["header_name"] == keys["value"][0]:
						for field in headers_t["fields"]:
							if field[0] == keys["value"][1]:
								headers_t["last_header"] = False
								print "Found match key in " + states["name"] + ". Key is "\
										+ headers_t["header_name"] + "." + field[0]
								headers_t["key_name"] = field[0]
								headers_t["key_position"] = field[1]
								headers_t["key_size"] = field[2]
								headers_t["key_type"] = "ap_uint<" + str(headers_t["key_size"]) + ">"

								# Evaluate state transitions
								for transitions in states["transitions"]:
									transition_tuple = [None]*5
									if transitions["type"] == "default":
										continue
									else:
									    print "Found state transition from "\
									    + headers_t["header_name"] + " to " + transitions["next_state"]

									    transition_tuple[0] = transitions["value"]
									    transition_tuple[1] = transitions["mask"] if transitions["mask"]!=None else str((1 << headers_t["key_size"]) - 1)
									    transition_tuple[2] = transitions["next_state"]
									    transition_tuple[3] = 0		# Here goes the ID
									    transition_tuple[4] = ""	# Header name
									    headers_t["transition_keys"].append(transition_tuple)

        # Final adjusts to retrieve max header number and pipeline laytout
	transition_id = []
	header_sizes_id = []
	header_size = 0
	for headers_t in headers_list:
                headers_t["next_state"].append("end")
		headers_t["next_state_id"].append(255)
		headers_t["key_number"] = len(headers_t["transition_keys"])
		transition_id.append(headers_t["parser_state_id"])
		header_sizes_id.append(headers_t["header_size"])
		header_size+=headers_t["header_size"]
		for headers_tt in headers_list:
			for state in headers_t["transition_keys"]:
				if headers_tt["parser_state"] == state[2] and\
                                        not headers_tt["header_name"] in headers_t["next_state"]:
					headers_t["next_state"].append(headers_tt["header_name"])
					headers_t["next_state_id"].append(headers_tt["parser_state_id"])
					state[3] = headers_tt["parser_state_id"]
					state[4] = headers_tt["header_name"]
					# Necessary to identify nodes with more than one source (proper mux insertion)
					headers_tt["previous_state"].append(headers_t["header_name"])
					headers_tt["previous_state_id"].append(headers_t["parser_state_id"])
					previous_state_tuple = [None]*2
					previous_state_tuple[0] = headers_t["header_name"]
					previous_state_tuple[1] = headers_t["parser_state_id"]
					headers_tt["previous_state_both"].append(previous_state_tuple)

        # Graph transformation
        node_list, nodes_levels = transf_graph(headers_list)

	for headers_t in headers_list:
            #print headers_t["header_name"]  + ": " + str(headers_t["header_size"]) + " bytes"
            headers_t["next_state"].remove("end")
	    headers_t["next_state_id"].remove(255)

        input_parser_state = min(transition_id)
	max_supp_headers = max(transition_id)
	max_header_size = max(header_sizes_id)
	header_num = len(header_sizes_id)
	header_size_avg = int(math.ceil(header_size/header_num))
	return headers_list, input_parser_state, max_supp_headers, max_header_size, header_num, header_size_avg, node_list, nodes_levels 

##############################################################
# Write the header layout types
##############################################################
def write_headers_template(headers_list, max_supp_headers, max_header_size, header_num):
	print "Generating Header Layouts..."
	with open("parser_header_template.hpp", "w") as parser_header_template:
		parser_header_template.write("/******************************************************************************" + "\n")
		parser_header_template.write("* parser_header_template: Self-generated template structs for the parser      *" + "\n")
		parser_header_template.write("* Jeferson Santiago da Silva (eng.jefersonsantiago@gmail.com)                 *" + "\n")
		parser_header_template.write("******************************************************************************/" + "\n")
		parser_header_template.write("\n#include <iostream>" + "\n")
		parser_header_template.write("#include <math.h>" + "\n")
		parser_header_template.write("#include <string>" + "\n")
		parser_header_template.write("#include <array>" + "\n")

		parser_header_template.write("\n#include \"pktBasics.hpp\"" + "\n")

		parser_header_template.write("\n#ifndef _PARSER_HEADER_TEMP_HPP_" + "\n")
		parser_header_template.write("#define _PARSER_HEADER_TEMP_HPP_" + "\n")

		# Defines
		parser_header_template.write("\n#define HEADER_NUM " + str(header_num) + "\n")
		parser_header_template.write("\n#define MAX_SUPP_HEADERS " + str(max_supp_headers) + "\n")
		parser_header_template.write("\n#define MAX_HEADER_SIZE " + str(max_header_size) + "\n")
		parser_header_template.write("\n#define MAX_HEADER_SIZE_BITS bytes2Bits(MAX_HEADER_SIZE)\n")

                fixed_header = True
		for headers_t in headers_list:
			header_name = headers_t["header_name"]
			header_name_cap = string.upper(header_name)
			parser_header_template.write("\n#define " + header_name_cap + "_HEADER_SIZE " + str(headers_t["header_size"])  + "\n")
			parser_header_template.write("\n#define " + header_name_cap + "_HEADER_SIZE_BITS bytes2Bits(" + header_name_cap + "_HEADER_SIZE)" + "\n")
			parser_header_template.write("\n#define " + header_name_cap + "_NUM_FIELDS " + str(headers_t["num_fields"]) + "\n")
                        header_layout = "HeaderFormat"
                        if headers_t["var_size_header"] or fixed_header:
                            if fixed_header:
                                header_der_layout = "FixedHeaderFormat"
                            else:
                                header_der_layout = header_name + "HeaderFormat"
                            # Redefining header template for variable sized headers
                            parser_header_template.write("template<uint16_t N_Size, uint16_t N_Fields, typename T_Key, uint16_t N_Key, uint16_t N_MaxSuppHeaders, uint16_t N_HeaderLenArrSize, uint16_t N_HeaderLenELemBits> " + "\n") 
                            parser_header_template.write("struct " + header_der_layout + " : public HeaderFormat<N_Size, N_Fields, T_Key, N_Key, N_MaxSuppHeaders, N_HeaderLenArrSize, N_HeaderLenELemBits, const " + header_der_layout + "<N_Size, N_Fields, T_Key, N_Key, N_MaxSuppHeaders, N_HeaderLenArrSize, N_HeaderLenELemBits>> { " + "\n") 
	                    #parser_header_template.write("\ttemplate <typename... T>  " + "\n")  
	                    #parser_header_template.write("\t" + header_layout + "(T... args) : HeaderFormat<N_Size, N_Fields, T_Key, N_Key, N_MaxSuppHeaders>(args...){} " + "\n")   

                            
                            parser_header_template.write("\t" + header_der_layout + " (ap_uint<bytes2Bits(N_Size)> PHVMask, " + "\n")  
	                    parser_header_template.write("\t\tstd::array<FieldFormat<N_Size>, N_Fields> Fields, " + "\n")  
	                    parser_header_template.write("\t\tstd::array<KeyFormat<T_Key, N_MaxSuppHeaders>, N_Key> Key, " + "\n")  
	                    parser_header_template.write("\t\tstd::pair<ap_uint<numbits(bytes2Bits(N_Size))>, ap_uint<numbits(bytes2Bits(N_Size))>> KeyLocation, " + "\n")  
	                    parser_header_template.write("\t\tbool LastHeader," + "\n") 					
	                    parser_header_template.write("\t\tIF_SOFTWARE(std::string HeaderName,)" + "\n")   
	                    parser_header_template.write("\t\tbool varSizeHeader," + "\n") 				
                            parser_header_template.write("\t\tstd::pair<ap_uint<numbits(bytes2Bits(N_Size))>, ap_uint<numbits(bytes2Bits(N_Size))>> HeaderLengthInd, std::array<ap_uint<N_HeaderLenELemBits>, N_HeaderLenArrSize> ArrLenLookup) : " + "\n")  
                            parser_header_template.write("\tHeaderFormat<N_Size, N_Fields, T_Key, N_Key, N_MaxSuppHeaders, N_HeaderLenArrSize, N_HeaderLenELemBits, const " + header_der_layout + "<N_Size, N_Fields, T_Key, N_Key, N_MaxSuppHeaders, N_HeaderLenArrSize, N_HeaderLenELemBits>> ({PHVMask, " + "\n")  
	                    parser_header_template.write("\t\tFields, " + "\n")  
	                    parser_header_template.write("\t\tKey, " + "\n")  
	                    parser_header_template.write("\t\tKeyLocation, " + "\n")  
	                    parser_header_template.write("\t\tLastHeader," + "\n") 					
	                    parser_header_template.write("\t\tIF_SOFTWARE(HeaderName,)" + "\n")   
	                    parser_header_template.write("\t\tvarSizeHeader," + "\n") 				
                            parser_header_template.write("\t\tHeaderLengthInd," + "\n")      
                            parser_header_template.write("\t\tArrLenLookup}) {}" + "\n")      
                            
                            parser_header_template.write("\n\tvoid getSpecHeaderSize(ap_uint<numbits(bytes2Bits(N_Size))>& size, "\
                                                            "const ap_uint<" + str(headers_t["header_length_size"]) + ">& " \
                                                            + headers_t["header_length_field"] + ") const {" + "\n") 
                            if fixed_header or not headers_t["var_size_header"]:
                                parser_header_template.write("\t\tsize = bytes2Bits(N_Size);" + "\n")
                                fixed_header = False
                            else:
                                parser_header_template.write("\t\tsize = " + str(headers_t["header_length_expression"]) + ";" + "\n") 
                            parser_header_template.write("\t}" + "\n")
                            parser_header_template.write("};" + "\n")
                        if not headers_t["var_size_header"]:
                                header_der_layout = "FixedHeaderFormat"
                        else:
                                header_der_layout = header_name + "HeaderFormat"
			# Header layout declaration
			if headers_t["last_header"]:
			    headers_t["key_number"] = 1
			parser_header_template.write("\nstatic const " + header_der_layout + "<" + str(headers_t["header_size"]) + ", "		\
											+ str(headers_t["num_fields"]) + ", " + headers_t["key_type"]	\
											+ ", " + str(headers_t["key_number"]) + ", MAX_SUPP_HEADERS "	\
											+ ", " + str(headers_t["header_length_larray_size"]) \
                                                                                        + ", " + str(headers_t["len_bit_size"]) 
                                                                                        + "> " + headers_t["header_type_name"] + "\n")
			parser_header_template.write( "{" + "\n")

			# Extract mask
			parser_header_template.write(  "\t(ap_uint<" + str(headers_t["header_size_bits"])   \
						+ ">(\"" + str(headers_t["extr_mask"]) + "\"))," + "\n")

			# Header Fileds
			#field_str = "\t{\n\t\t{"
                        field_str = "\tstd::array<FieldFormat< " + str(headers_t["header_size"]) + ">," + str(headers_t["num_fields"]) + ">{\n\t\t{"

                        for field in range(headers_t["num_fields"]):
				field_str =  field_str + "\n\t\t\t{" + str(headers_t["fields"][field][1]) + ", "	\
					+ str(headers_t["fields"][field][2]) + " IF_SOFTWARE(, \""		\
					+ str(headers_t["fields"][field][0]) + "\")}"
				if field == headers_t["num_fields"] - 1:
					field_str =  field_str + "\n\t\t},\n\t},"
				else:
					field_str =  field_str + ","
			parser_header_template.write( field_str	 + "\n")

			# Match Keys
			#key_str = "\t{\n\t\t{"
			key_str = "\tstd::array<KeyFormat<" + headers_t["key_type"] + ", " + str(max_supp_headers) + ">," + str(headers_t["key_number"]) + ">{\n\t\t{"
			it = 0
			num_keys = len(headers_t["transition_keys"])
			if headers_t["last_header"]:
				key_str =  key_str + "\n\t\t\t{1, 1, 0 IF_SOFTWARE(, \"Last Header\")}\n\t\t},\n\t},"
			else:
				for trans in headers_t["transition_keys"]:
					key_str =  key_str + "\n\t\t\t{" + str(trans[0]) + ", "					\
								+ str(trans[1]) + ", " + str(trans[3]) + " IF_SOFTWARE(, \""	\
								+ str(trans[4]) + "\")}"
					if it == num_keys - 1:
						key_str =  key_str + "\n\t\t},\n\t},"
					else:
						key_str =  key_str + ","
					it+=1
			parser_header_template.write(key_str + "\n")

			# Key position
			parser_header_template.write( "\tstd::pair<ap_uint<" + str(int.bit_length(headers_t["header_size_bits"]))   \
					+ ">, ap_uint<" + str(int.bit_length(headers_t["header_size_bits"]))				\
					+ ">>{" + str(headers_t["key_position"]) + "," + str(headers_t["key_size"]) + "}," + "\n")

			# Last Header
			parser_header_template.write("\t(" + string.lower(str(headers_t["last_header"])) + ")," + "\n")

			#Header Layout name
			parser_header_template.write("\tIF_SOFTWARE(\"" + headers_t["header_type_name"] + "\",)" + "\n")

			# Variable Size Flag
			parser_header_template.write("\t(" + string.lower(str(headers_t["var_size_header"])) + ")," + "\n")

			# Variable Size indicator position
			parser_header_template.write( "\tstd::pair<ap_uint<" + str(int.bit_length(headers_t["header_size_bits"]))   \
			    		+ ">, ap_uint<" + str(int.bit_length(headers_t["header_size_bits"]))				\
			    		+ ">>{" + str(headers_t["header_length_position"]) + "," + str(headers_t["header_length_size"]) + "}," + "\n")

                        # Initialize pipeline adjust for variable sized headers
			#parser_header_template.write( "\tstd::array<ap_uint<" + str(headers_t["len_bit_size"]) + ">, " + str(headers_t["header_length_larray_size"]) + ">({")
			parser_header_template.write("\t{{")
                        it = 0
                        for i in headers_t["header_length_lookup_array"]:
			    it+=1
                            parser_header_template.write(str(i))
                            if it < headers_t["header_length_larray_size"]:
			        parser_header_template.write(",")
			#parser_header_template.write("})" + "\n")
			parser_header_template.write("}}" + "\n")

                        # End of declaration
			parser_header_template.write("};" + "\n")


		parser_header_template.write("\n#endif //_PARSER_HEADER_TEMP_HPP_"  + "\n")

##############################################################
# Write the parser pipeline
##############################################################
def write_parse_pipeline(headers_list, bus_size, max_pkt_id_size, input_parser_state, max_supp_headers, node_list, nodes_levels):

        num_graph_levels = max(nodes_levels) + 1

        ##############
	# Parser.hpp #
	##############
	with open("Parser.hpp", "w") as Parser:
		Parser.write("/******************************************************************************" + "\n")
		Parser.write("* Packet Parser: header extraction and supported protocols graph              *" + "\n")
		Parser.write("* Jeferson Santiago da Silva (eng.jefersonsantiago@gmail.com)                 *" + "\n")
		Parser.write("******************************************************************************/" + "\n")

		Parser.write("\n#include \"Header.hpp\"" + "\n")
		Parser.write("\n#include \"parser_header_template.hpp\"" + "\n")

		Parser.write("\n#ifndef _PARSER_HEADER_HPP_" + "\n")
		Parser.write("\n#define _PARSER_HEADER_HPP_" + "\n")

		Parser.write("\n#define PKT_BUS_SIZE " + str(bus_size) + "\n")
		Parser.write("\n#define MAX_PKT_ID_SIZE " + str(max_pkt_id_size) + "\n")

		Parser.write("\ntypedef PacketData<PKT_BUS_SIZE, MAX_SUPP_HEADERS, MAX_PKT_ID_SIZE> PktIOData;\n")
		Parser.write("typedef std::array<PktIOData, MAX_SUPP_HEADERS + 1>  PipePktDataArr;\n")
		
                for headers_t in headers_list:
			header_name = headers_t["header_name"]
			header_name_cap = string.upper(header_name)
	                Parser.write("typedef PHVData<" + header_name_cap + "_HEADER_SIZE, MAX_SUPP_HEADERS, MAX_PKT_ID_SIZE> " + header_name + "PHVData;\n")	
                
                Parser.write("\nvoid HeaderAnalysisTop(\n\tconst PktIOData& PacketIn")
		for headers_t in headers_list:
			header_name = headers_t["header_name"]
			header_name_cap = string.upper(header_name)
			Parser.write(",\n\t" + header_name + "PHVData& " + header_name + "_PHV")
		Parser.write(",\n\tPktIOData& PacketOut);" + "\n")

		Parser.write("\n#endif //_PARSER_HEADER_HPP_" + "\n")

	##############
	# Parser.cpp #
	##############
	print "Generating Parser Pipeline..."

        simpl_graph = AGraph(directed=True, acyclic=True)
	with open("Parser.cpp", "w") as Parser:
		Parser.write("/******************************************************************************" + "\n")
		Parser.write("* Packet Parser: header extraction and supported protocols graph              *" + "\n")
		Parser.write("* Jeferson Santiago da Silva (eng.jefersonsantiago@gmail.com)                 *" + "\n")
		Parser.write("******************************************************************************/" + "\n")

		Parser.write("\n#include \"Parser.hpp\"" + "\n")

                Parser.write("\nvoid HeaderAnalysisTop(\n\tconst PktIOData& PacketIn")
		for headers_t in headers_list:
			header_name = headers_t["header_name"]
			header_name_cap = string.upper(header_name)
			Parser.write(",\n\t" + header_name + "PHVData& " + header_name + "_PHV")
		Parser.write(",\n\tPktIOData& PacketOut){" + "\n")

		Parser.write("#pragma HLS INTERFACE ap_ctrl_none port=return" + "\n")
		Parser.write("#pragma HLS PIPELINE II=1" + "\n")
                #Parser.write("#pragma HLS LATENCY min=" + str(num_graph_levels)+ " max=" + str(num_graph_levels + 1) + "\n")
                Parser.write("#pragma HLS LATENCY min=" + str(num_graph_levels)+ " max=" + str(num_graph_levels) + "\n")
		Parser.write("/*Consider increase the max acceptable latency in case of clock violation*/\n")

		Parser.write("\n\t// Wires" + "\n")
		Parser.write("\tPipePktDataArr tmpPacketOut;" + "\n")
		Parser.write("#pragma HLS ARRAY_PARTITION variable=tmpPacketOut dim=1" + "\n")
		Parser.write("\tPipePktDataArr tmpPacketIn;" + "\n")
		Parser.write("#pragma HLS ARRAY_PARTITION variable=tmpPacketIn dim=1" + "\n")

		Parser.write("\n\t// Stateful objects" + "\n")
		for headers_t in headers_list:
			header_name = headers_t["header_name"]
			header_name_cap = string.upper(header_name)
                        header_layout = "FixedHeaderFormat"
                        header_inst = "FixedHeader"
                        if headers_t["var_size_header"]:
                            header_layout = header_name + "HeaderFormat"
                            header_inst = "VariableHeader"

                        Parser.write("\n#pragma HLS INTERFACE ap_ovld port=" + header_name + "_PHV")
                        #Parser.write("\n#pragma HLS INTERFACE register port=" + header_name + "_PHV")

			#Parser.write("\n\ttypedef " + header_inst +  "<" + header_name_cap + "_HEADER_SIZE, PKT_BUS_SIZE, MAX_PKT_SIZE, MAX_SUPP_HEADERS, MAX_PKT_ID_SIZE, "\
                        #                                "decltype(" + header_name + "_t), " + str(headers_t["header_length_larray_size"]) + ">  " + header_name + "_HeaderType;")
			Parser.write("\n\ttypedef " + header_inst +  "<" + header_name_cap + "_HEADER_SIZE, PKT_BUS_SIZE, MAX_PKT_SIZE, MAX_SUPP_HEADERS, MAX_PKT_ID_SIZE, "\
                                                        "decltype(" + headers_t["header_type_name"] + ")>  " + header_name + "_HeaderType;")
			#Parser.write("\n\tstatic Header<" + header_name_cap + "_HEADER_SIZE, PKT_BUS_SIZE, MAX_PKT_SIZE, MAX_SUPP_HEADERS, MAX_PKT_ID_SIZE, "\
                        #                                "decltype(" + header_name + "_t), " + str(headers_t["header_length_larray_size"]) + ", " + header_name + "_HeaderType> "\
			#				+ header_name + "(IF_SOFTWARE(\"" + header_name + "\",) " + str(headers_t["parser_state_id"]) + ", "\
			#				+ headers_t["header_type_name"] + ");" + "\n")
			Parser.write("\n\tstatic " + header_name + "_HeaderType " \
			    + header_name + "(IF_SOFTWARE(\"" + header_name + "\",) " + str(headers_t["parser_state_id"]) + ", "\
			    + headers_t["header_type_name"] + ");")

                        Parser.write("\n\tstatic std::array<" + header_name + "PHVData, 1> tmp_" + header_name + "_PHV;" + "\n")
			Parser.write("\n\t#pragma HLS DEPENDENCE variable=tmp_" + header_name + "_PHV false" + "\n")
			Parser.write("\n\t#pragma HLS ARRAY_PARTITION variable=tmp_" + header_name + "_PHV dim=1" + "\n")

                for headers_t in headers_list:
                    for nodes in node_list:
                        if nodes[0] == headers_t["header_name"]:
                            if nodes[1][1]:
                                #print nodes[0]
                                for nodess in node_list:
                                    if nodes[1][0] == nodess[1][0] and nodes[0] != nodess[0]:
                                        #print nodess[0]
                                        for headers_tt in headers_list:
                                            for ps in headers_tt["previous_state_both"]:
                                                if ps[0] == nodess[0]:
                                                    ttuple = [None]*2
                                                    ttuple[0] = headers_t["header_name"]
                                                    ttuple[1] = headers_t["parser_state_id"]
                                                    headers_tt["previous_state_both"].append(ttuple)
                                                    headers_tt["previous_state_id"].append(headers_t["parser_state_id"])
                                                    break

                max_level = max(nodes_levels)
                node_it = 0
                #print node_list
                simpl_graph.add_node('end')
                for nodes in node_list:
                        for headers_t in headers_list:
                            if headers_t["header_name"] == nodes[0]:
                                simpl_graph.add_node(nodes[0])
                                simpl_graph.add_edge((nodes[0], 'end'))
                                header_name = headers_t["header_name"]
                                header_type_name = headers_t["header_type_name"]
                                header_size = headers_t["header_size"]
			        header_state_id = headers_t["parser_state_id"]
			        previous_state_id = headers_t["previous_state_id"]
			        previous_state_both = headers_t["previous_state_both"]
                        
                        Parser.write("\n\t//---------------------------------------\n")
                        Parser.write("\t//" + header_name + "\n")
                        Parser.write("\t//---------------------------------------\n")

			if header_state_id == input_parser_state:
                            print header_name + " <- Input Data"  
                            Parser.write("\n\ttmpPacketIn[" + str(input_parser_state) + "] = PacketIn;" + "\n")
                            node_it += 1
			else:
                            if len(previous_state_id) == 1:
                                simpl_graph.add_edge((previous_state_both[0][0], header_name))
                                print header_name + " <- " + previous_state_both[0][0]  
			        Parser.write("\n\ttmpPacketIn[" + str(header_state_id) + "] = tmpPacketOut[" + str(previous_state_id[0]) +"];" + "\n")
			    else:
                                it = 0
				#for headers_tt in headers_list:
                                #    if node_list[node_it - 1][0] == headers_tt["header_name"]:
                                #        Parser.write("\n\t\ttmpPacketIn[" + str(header_state_id) + \
                                #                                "] = tmpPacketOut[" + str(headers_tt["parser_state_id"]) +"];" + "\n") 
                                #        node_it += 1
                                #        break
                                for previous_states in previous_state_both:
				    for nodess in node_list:
                                        if nodess[0] == previous_states[0]:
                                            if nodess[1][0] == nodes[1][0] - 1:
                                                for headers_tt in headers_list:
                                                    if headers_tt["header_name"] == nodess[0]:
                                                        if not nodess[1][1]:
                                                            it+=1

				for previous_states in previous_state_both:
				    for nodess in node_list:
                                        if nodess[0] == previous_states[0]:
                                            if nodess[1][0] == nodes[1][0] - 1:
                                                simpl_graph.add_edge((nodess[0], header_name))
                                                print header_name + " <- " + nodess[0]
                                                for headers_tt in headers_list:
                                                    if headers_tt["header_name"] == nodess[0]:
                                                        if nodess[1][1] or (header_name in headers_tt["next_state"] and it > 1):
       			                                    Parser.write("\n\tif (tmp_" + str(nodess[0]) + "_PHV[0]" +\
                                                                    #str(headers_tt["parser_state_id"]) + "].Valid)" + "\n")
                                                                    ".Valid)" + "\n")
        			                        Parser.write("\n\t\ttmpPacketIn[" + str(header_state_id) + \
                                                                "] = tmpPacketOut[" + str(headers_tt["parser_state_id"]) +"];" + "\n")

			Parser.write("\n\t" + header_name + ".HeaderAnalysis(tmpPacketIn[" + str(header_state_id) + "], " \
						#"wire_" + header_name + "_PHV, tmpPacketOut[" + str(header_state_id) + "]);" + "\n")
                                                "tmp_" + header_name + "_PHV[0], tmpPacketOut[" + str(header_state_id) + "]);" + "\n")

                        #Parser.write("\n\t"  + "tmp_" + header_name + "_PHV[0].Data = " + "wire_" + header_name + "_PHV.Data & " + header_type_name + ".PHVMask;")

                        #Parser.write("\n\t"  + "tmp_" + header_name + "_PHV[0].ExtractedBitNum = " + "wire_" + header_name + "_PHV.ExtractedBitNum;")
                        #Parser.write("\n\t"  + "tmp_" + header_name + "_PHV[0].Valid = " + "wire_" + header_name + "_PHV.Valid;")
                        #Parser.write("\n\t"  + "tmp_" + header_name + "_PHV[0].ValidPulse = " + "wire_" + header_name + "_PHV.ValidPulse;")
                        #Parser.write("\n\t"  + "tmp_" + header_name + "_PHV[0].ID = " + "wire_" + header_name + "_PHV.ID;")
                        #Parser.write("\n\t"  + "tmp_" + header_name + "_PHV[0].PktID = " + "wire_" + header_name + "_PHV.PktID;")
                        #Parser.write("\n\t"  + "IF_SOFTWARE(tmp_" + header_name + "_PHV[0].Name = " + "wire_" + header_name + "_PHV.Name;)")
			#Parser.write("\n\t" + header_name + "_PHV = tmp_" + header_name + "_PHV[0];" + "\n")

                        Parser.write("\n\t"  + header_name + "_PHV.Data = (" + header_type_name + ".PHVMask == 0) ? ap_uint<bytes2Bits(" + str(header_size)  + ")>(0) :  tmp_" + header_name + "_PHV[0].Data & " + header_type_name + ".PHVMask;")

                        Parser.write("\n\t"  + header_name + "_PHV.ExtractedBitNum = " + "tmp_" + header_name + "_PHV[0].ExtractedBitNum;")
                        Parser.write("\n\t"  + header_name + "_PHV.Valid = " + "tmp_" + header_name + "_PHV[0].Valid;")
                        Parser.write("\n\t"  + header_name + "_PHV.ValidPulse = " + "tmp_" + header_name + "_PHV[0].ValidPulse;")
                        Parser.write("\n\t"  + header_name + "_PHV.ID = " + "tmp_" + header_name + "_PHV[0].ID;")
                        Parser.write("\n\t"  + header_name + "_PHV.PktID = " + "tmp_" + header_name + "_PHV[0].PktID;")
                        Parser.write("\n\t"  + "IF_SOFTWARE(" + header_name + "_PHV.Name = " + "tmp_" + header_name + "_PHV[0].Name;)")
                ## Connecting last stage pipe
                Parser.write("\n\t//---------------------------------------\n")
                Parser.write("\t//Output data bus\n")
                Parser.write("\t//---------------------------------------\n")

                first = True
                for headers_t in headers_list:
		    if headers_t["last_header"]:
                        for nodes in node_list:
                            if nodes[1][0] == max_level and nodes[0] == headers_t["header_name"]:
                                header_name = headers_t["header_name"]
		                header_state_id = headers_t["parser_state_id"]
                                if first:
                                    #Parser.write("\n\tif (tmp_" + str(header_name) + "_PHV[" + str(header_state_id) +"].Valid)" + "\n")
                                    Parser.write("\n\tif (tmp_" + str(header_name) + "_PHV[0].Valid)" + "\n")
                                    first = False
                                else:
                                    if header_state_id != max_supp_headers:
                                        #Parser.write("\n\telse if (tmp_" + str(header_name) + "_PHV[" + str(header_state_id) +"].Valid)" + "\n")
                                        Parser.write("\n\telse if (tmp_" + str(header_name) + "_PHV[0].Valid)" + "\n")

                                    else:
                                        Parser.write("\n\telse" + "\n")
                                Parser.write("\n\t\tPacketOut = tmpPacketOut[" + str(header_state_id) +"];" + "\n")
                                break

		Parser.write("\n}\n")
        draw_graph(simpl_graph.tred(copy=True), 'simpl_graph.pdf')

##############################################################
# Main
##############################################################
def main():

	if len(sys.argv) != 4:
		param = len(sys.argv) - 1
		print "Invalid parameter number. Expected 3 parameters, got %d" % param
		print "Usage python generate_header_parser.py <json_file> <bus_size> <max_pkt_id_size>"
		return

	json_file = sys.argv[1]
	bus_size = sys.argv[2]
	max_pkt_id_size = sys.argv[3]

	headers_list, input_parser_state, max_supp_headers, max_header_size, header_num, header_size_avg, node_list, nodes_levels  = json_parser(json_file)
	write_headers_template(headers_list, max_supp_headers, max_header_size, header_num)
	write_parse_pipeline(headers_list, bus_size, max_pkt_id_size, input_parser_state, max_supp_headers, node_list, nodes_levels)
	print "Parsing Done"

if __name__ == '__main__':
	main()
