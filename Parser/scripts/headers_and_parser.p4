/*
 * Jeferson Santiago da Silva
 */

#define TEST_VAR_HEADER 0
#define TESTABLE 0
//#define BITNUM 992
#define BITNUM 224

// Ethernet
header_type ethernet_t {
    fields {
        bit<48> dstAddr;
        bit<48> srcAddr;
        bit<16> etherType;
    }
}

header_type vlan_outer_t {
    fields {
        bit<3> PCP;
        bit<1> DEI;
        bit<12> VID;
        bit<16> etherType;
    }
}

header_type vlan_inner_t {
    fields {
        bit<3> PCP;
        bit<1> DEI;
        bit<12> VID;
        bit<16> etherType;
    }
}

header_type vlan_t {
    fields {
        bit<3> PCP;
        bit<1> DEI;
        bit<12> VID;
        bit<16> etherType;
    }
}

header_type mpls_outer_t {
    fields {
        bit<20> label;
        bit<3> TC;
        bit<1> S;
        bit<8> TTL;
    }
}

header_type mpls_inner_t {
    fields {
        bit<20> label;
        bit<3> TC;
        bit<1> S;
        bit<8> TTL;
    }
}

// IP header
header_type ipv4_t {
    fields {
        bit<4>  version;
        bit<4>  ihl;
        bit<8>  diffserv;
        bit<16> totalLen;
        bit<16> identification;
        bit<3> flags;
        bit<13> fragOffset;
        bit<8>  ttl;
        bit<8>  protocol;
        bit<16> hdrChecksum;
        bit<32> srcAddr;
        bit<32> dstAddr;
    }
}

// IP header
header_type ipv4_var_t {
    fields {
        bit<4>  version;
        bit<4>  ihl;
        bit<8>  diffserv;
        bit<16> totalLen;
        bit<16> identification;
        bit<3> flags;
        bit<13> fragOffset;
        bit<8>  ttl;
        bit<8>  protocol;
        bit<16> hdrChecksum;
        bit<32> srcAddr;
        bit<32> dstAddr;
		varbit<320> options;
    }
	length : 4*ihl;
}

// IPv6
header_type ipv6_t {
    fields {
        bit<4> version;
        bit<8> trafficClass;
        bit<20> flowLabel;
        bit<16> payloadLen;
        bit<8> nextHdr;
        bit<8> hopLimit;
        bit<128> srcAddr;
        bit<128> dstAddr;
    }
}

// IPv6 extension #1
header_type ipv6_ext_1_t {
    fields {
        bit<8> nextHdr;
        bit<8> totalLen;
        bit<16> stuff;
		varbit<BITNUM> options;
    }
	length : 8*(totalLen + 1);
	//length : 8*totalLen + 8;
}

// IPv6 extension #2
header_type ipv6_ext_2_t {
    fields {
        bit<8> nextHdr;
        bit<8> totalLen;
        bit<16> stuff;
		varbit<BITNUM> options;
    }
	length : 8*(totalLen + 1);
	//length : 8*totalLen + 8;
}

// UDP header
header_type udp_t {
    fields {
        bit<16> srcPort;
        bit<16> dstPort;
        bit<16> hdrLength;
        bit<16> chksum;
    }
}

// TCP header
header_type tcp_t {
    fields {
        bit<16> srcPort;
        bit<16> dstPort;
        bit<32> seqNum;
        bit<32> ackNum;
        bit<4> dataOffset;
        bit<6> unused;
        bit<6> flags;
        bit<16> windowSize;
        bit<16> chksum;
        bit<16> urgPtr;
    }
}

// ICMP header
header_type icmp_t {
    fields {
        bit<8> mtype;
        bit<8> code;
        bit<16> chksum;
        bit<16> body;
    }
}

header ethernet_t ethernet;
#if TESTABLE
header vlan_t vlan;
#else
header vlan_outer_t outer_vlan;
header vlan_inner_t inner_vlan;
header mpls_outer_t outer_mpls;
header mpls_inner_t inner_mpls;
header ipv6_ext_1_t ipv6_ext_1;
header ipv6_ext_2_t ipv6_ext_2;
header icmp_t icmp;
#endif
#if TEST_VAR_HEADER ==0
header ipv4_t ipv4;
#else
header ipv4_var_t ipv4_var;
#endif
header ipv6_t ipv6;
header udp_t udp;
header tcp_t tcp;

parser start {
    return parse_ethernet;
}

parser parse_ethernet {
    extract(ethernet);
    return select(ethernet.etherType) {
#if TEST_VAR_HEADER
        0x0800    : parse_ipv4_var;
#else
        0x0800    : parse_ipv4;
#endif
#if TESTABLE
        0x8100    : parse_vlan;
#else
        0x8100    : parse_inner_vlan;
        0x9100    : parse_outer_vlan;
        0x8847    : parse_outer_mpls;
#endif
        0x86DD    : parse_ipv6;
        default   : ingress;
    }
}

#if TESTABLE
parser parse_vlan {
    extract(vlan);
    return select(vlan.etherType) {
#if TEST_VAR_HEADER
        0x0800    : parse_ipv4_var;
#else
        0x0800    : parse_ipv4;
#endif
        0x86DD    : parse_ipv6;
        default   : ingress;
    }
}

#else
parser parse_outer_vlan {
    extract(outer_vlan);
    return select(outer_vlan.etherType) {
        0x8100    : parse_inner_vlan;
        default   : ingress;
    }
}

parser parse_inner_vlan {
    extract(inner_vlan);
    return select(inner_vlan.etherType) {
#if TEST_VAR_HEADER
        0x0800    : parse_ipv4_var;
#else
        0x0800    : parse_ipv4;
#endif
        0x86DD    : parse_ipv6;
        default   : ingress;
    }
}

parser parse_outer_mpls {
    extract(outer_mpls);
    return select(outer_mpls.TC) {
        0		  : parse_inner_mpls;
        default   : ingress;
    }
}

parser parse_inner_mpls {
    extract(inner_mpls);
    return ingress;
}
#endif

#if TEST_VAR_HEADER == 0
parser parse_ipv4 {
    extract(ipv4);
    return select(ipv4.protocol){
#if TESTABLE == 0
        0x01      : parse_icmp;
#endif
        0x11      : parse_udp;
        0x06      : parse_tcp;
        default   : ingress;
    }
}

#else
parser parse_ipv4_var {
    extract(ipv4_var);
    return select(ipv4_var.protocol){
#if TESTABLE == 0
        0x01      : parse_icmp;
#endif
        0x11      : parse_udp;
        0x06      : parse_tcp;
        default   : ingress;
    }
}
#endif

parser parse_ipv6 {
    extract(ipv6);
    return select(ipv6.nextHdr){
#if TESTABLE == 0
		0x00	  : parse_ipv6_ext_1;
        0x3a      : parse_icmp;
#endif
        0x11      : parse_udp;
        0x06      : parse_tcp;
        default   : ingress;
    }
}

parser parse_udp {
    extract(udp);
    return ingress;
}

parser parse_tcp {
    extract(tcp);
    return ingress;
}

#if TESTABLE == 0
parser parse_ipv6_ext_1 {
    extract(ipv6_ext_1);
    return select(ipv6_ext_1.nextHdr){
        0x3a      : parse_icmp;
		0x3c   	  : parse_ipv6_ext_2;
        0x11      : parse_udp;
        0x06      : parse_tcp;
        default   : ingress;
    }    
}

parser parse_ipv6_ext_2 {
    extract(ipv6_ext_2);
    return select(ipv6_ext_2.nextHdr){
        0x3a      : parse_icmp;
        0x11      : parse_udp;
        0x06      : parse_tcp;
        default   : ingress;
    }    
}

parser parse_icmp {
    extract(icmp);
    return ingress;
}
#endif

#if TEST_VAR_HEADER == 0
field_list ipv4_checksum_list {
    ipv4.version;
    ipv4.ihl;
    ipv4.diffserv;
    ipv4.totalLen;
    ipv4.identification;
    ipv4.flags;
    ipv4.fragOffset;
    ipv4.ttl;
    ipv4.protocol;
    ipv4.srcAddr;
    ipv4.dstAddr;
}
#endif

control ingress {
}

control egress {
}
