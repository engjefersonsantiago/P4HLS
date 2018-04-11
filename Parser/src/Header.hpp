/******************************************************************************
* Packet Header: Header basic class for FPGA packet processing                *
* Jeferson Santiago da Silva (eng.jefersonsantiago@gmail.com)                 *
******************************************************************************/

#include <iostream>
#include <cmath>
#include <string>
#include <array>
#include <tuple>
#include <type_traits>
#include <cstdint>

#include "defined_types.h"
#include "pktBasics.hpp"

// Define to enable lookup implementation
#define LOOKUPTABLE_FOR_SHIFT_CALC 1
#define LOOKUPTABLE_FOR_OUT_BUS_SHIFT_CALC 1

// Needs to be defined to force packet bypass
#define ENABLE_STATE_BYPASS

#ifndef _PKT_HEADER_HPP_
#define _PKT_HEADER_HPP_
// Template Parameters:
// N_Size: Header size in bytes
// N_BusSize: Data bus size in bits
// N_MaxPktSize: Max packet size in bytes
// N_MaxSuppHeaders: Max number of supported headers
// N_MaxPktId: Max packet packet ID (in bits)
// Construction parameters:
// instance_name: human readable name of the object instance
// instance_id: unique class instance identifier
// HLayout: header layout structure for the processed header
// T_DHeader: type of the derived header for CRTP purposes
template<uint16_t N_Size, uint16_t N_BusSize, uint16_t N_MaxPktSize,
	uint16_t N_MaxSuppHeaders, uint8_t N_MaxPktId, typename T_HeaderLayout,
	typename T_DHeader>
class Header {
    protected:

		// Config Params as structs: static constexpr

		// Defines here to fix template parameters passage
		static constexpr uint16_t BUS_SIZE_LENGTH = numbits(N_BusSize);
		static constexpr uint16_t HEADER_SIZE_IN_BITS = bytes2Bits(N_Size);
		static constexpr uint16_t PKT_SIZE_IN_BITS = bytes2Bits(N_MaxPktSize);
		static constexpr uint16_t DATAOUT_STUFF_SIZE = bus_stuff_wraparound(
														HEADER_SIZE_IN_BITS,
														N_BusSize,
														HEADER_SIZE_IN_BITS);
		static constexpr uint16_t DATAOUT_STUFF_SHIFT = N_BusSize -
														DATAOUT_STUFF_SIZE;
		static constexpr uint16_t RECEIVED_MAX_WORDS = DivAndCeil(
														HEADER_SIZE_IN_BITS,
														N_BusSize);
		static constexpr uint16_t GREATER_BUS_OR_HEADER_SIZE =
			max(HEADER_SIZE_IN_BITS, N_BusSize);
		static constexpr uint16_t RECEIVED_WORDS_SIZE =
			numbits(RECEIVED_MAX_WORDS);
		static constexpr uint16_t RECEIVED_BITS_SIZE =
			numbits(PKT_SIZE_IN_BITS);
	    static constexpr uint16_t ARR_LOOK_LEN_SIZE =
	    	std::tuple_size<decltype(T_HeaderLayout::ArrLenLookup)>::value;

		//User types
		typedef PacketData<N_BusSize, N_MaxSuppHeaders, N_MaxPktId>
			PacketDataType;
		typedef PHVData<N_Size, N_MaxSuppHeaders, N_MaxPktId> PHVDataType;
		typedef ap_uint<HEADER_SIZE_IN_BITS> ExtractedHeaderType;
		typedef ap_uint<numbits(GREATER_BUS_OR_HEADER_SIZE)>
			busOrHeaderBitsuType;
		typedef ap_int<numbits(GREATER_BUS_OR_HEADER_SIZE) + 1>
			busOrHeaderBitsType;
		typedef std::array<ap_uint<HEADER_SIZE_IN_BITS>, RECEIVED_MAX_WORDS>
			ExtractedHeaderPipeType;
		typedef ap_uint<RECEIVED_WORDS_SIZE> receivedWordsType;
		typedef ap_uint<RECEIVED_BITS_SIZE> receivedBitsType;
		typedef ap_uint<numbits(N_MaxSuppHeaders)> headerIDType;
		typedef std::array<ap_uint<BUS_SIZE_LENGTH>, ARR_LOOK_LEN_SIZE>
			headerLenArrSizeType;

		// Data members
		IF_SOFTWARE(const std::string instance_name;)
		const headerIDType instance_id;

		const T_HeaderLayout HeaderLayout;

		bool HeaderIdle;
		bool HeaderDone;
		bool HeaderDonePulse;
		bool HeaderException;

		headerIDType NextHeader;
		bool NextHeaderValid;

		ExtractedHeaderType ExtractedHeader;
		const bool skipExtraction;
		receivedWordsType receivedWords;
		receivedBitsType receivedBits;
		PacketDataType PacketOutReg;

		const busOrHeaderBitsuType stateTransShiftVal;
		const std::array<busOrHeaderBitsType, RECEIVED_MAX_WORDS>
			shiftNumLookup;
		const busOrHeaderBitsuType headerLengthShiftVal;

		bool headerSizeValid;
		ap_uint<numbits(HEADER_SIZE_IN_BITS)> headerSize;
		ap_uint<numbits(HEADER_SIZE_IN_BITS)> LenVal;

		const ap_uint<N_BusSize> busSizeMask;
		const headerLenArrSizeType HeaderLessBusStuffShift;
		const headerLenArrSizeType HeaderLessBusStuffRShift;
		const headerLenArrSizeType HeaderGreaterBusStuffShift;
		const headerLenArrSizeType HeaderGreaterBusStuffRShift;
		const std::array<bool, ARR_LOOK_LEN_SIZE> HeaderBusCompVal;

	public:

		// Constructor
        Header(IF_SOFTWARE (const std::string& instance_name,)
        		const headerIDType& instance_id,
				const T_HeaderLayout& HLayout) :
				IF_SOFTWARE (instance_name{instance_name},)
				instance_id {instance_id},
				HeaderLayout (HLayout),
				HeaderIdle {true},
				HeaderDone {false},
				HeaderDonePulse {false},
				HeaderException {false},
				NextHeader {0},
				NextHeaderValid {false},
				skipExtraction {HLayout.PHVMask == 0},
				receivedWords {0},
				receivedBits {0},

				stateTransShiftVal { bus_stuff_wraparound(
										HEADER_SIZE_IN_BITS,
										N_BusSize,
										(HLayout.KeyLocation.first +
										HLayout.KeyLocation.second)
										)
									},
				shiftNumLookup (
					init_array<decltype(this), 0, decltype(shiftNumLookup)>
						([](size_t i) {
							return HEADER_SIZE_IN_BITS - (i+1)*N_BusSize;
						})
					),
				headerLengthShiftVal { bus_stuff_wraparound(
					HEADER_SIZE_IN_BITS,
					N_BusSize,
					(HLayout.HeaderLengthInd.first +
					HLayout.HeaderLengthInd.second)
					)
				},
				headerSizeValid {false},
				headerSize {HEADER_SIZE_IN_BITS},
				busSizeMask {ap_uint<N_BusSize>
							((ap_uint<N_BusSize>(1) << N_BusSize) - 1)
							},
				HeaderLessBusStuffShift (
					init_array<decltype(this), 0,
						decltype(HeaderLessBusStuffShift)>
						([this, HLayout](size_t i) {
							return busSizeMask & HLayout.ArrLenLookup[i];
						})
					),
				HeaderLessBusStuffRShift (
					init_array<decltype(this), 0,
						decltype(HeaderLessBusStuffRShift)>
						([this](size_t i) -> ap_uint<N_BusSize> {
							return N_BusSize - HeaderLessBusStuffShift[i];
						})
					),
				HeaderGreaterBusStuffShift (
					init_array<decltype(this), 0,
						decltype(HeaderGreaterBusStuffShift)>
						([HLayout](size_t i) -> ap_uint<N_BusSize> {
							return HLayout.ArrLenLookup[i];
						})
					),
				HeaderGreaterBusStuffRShift	(
					init_array<decltype(this), 0,
						decltype(HeaderGreaterBusStuffShift)>
						([HLayout](size_t i) -> ap_uint<N_BusSize> {
							return N_BusSize - HLayout.ArrLenLookup[i];
						})
					),
				HeaderBusCompVal (
					init_array<decltype(this), 0, decltype(HeaderBusCompVal)>
						([HLayout](size_t i) -> bool {
							return
								HLayout.ArrLenLookup[i] >> BUS_SIZE_LENGTH > 0;
						})
					)
		{} // Header(...)

        // General MISC information
        const uint16_t getHeaderSize() const { return N_Size; }
        const uint16_t getFieldNum() const {return HeaderLayout.Fields.size();}
        const uint16_t getOutStuffBits() const { return DATAOUT_STUFF_SIZE; }

        IF_SOFTWARE(
        void printFields() {
			for (const auto& field : HeaderLayout.Fields)
				std::cout << "Field: " << field.FieldName << '\n';
		}
        void printNextHeaders() {
			for (const auto& key : HeaderLayout.Key)
				std::cout << "Key: " << std::hex << key.KeyVal << \
					" Next Header: " << key.NextHeaderName << '\n';
		}
		const std::string getInstName() const {return instance_name;}
		) // IF_SOFTWARE

        headerIDType getInstId() const {return instance_id;}

		void StateTransition(const PacketDataType& PacketIn);
		void ExtractFields(const PacketDataType& PacketIn, PHVDataType& PHV);
		void PipelineAdjust(const PacketDataType& PacketIn,
							PacketDataType& PacketOut);
		void HeaderAnalysis(const PacketDataType& PacketIn,
							PHVDataType& PHV, PacketDataType& PacketOut);
};

// State transition function
template<uint16_t N_Size, uint16_t N_BusSize, uint16_t N_MaxPktSize,
	uint16_t N_MaxSuppHeaders, uint8_t N_MaxPktId, typename T_HeaderLayout,
	typename T_DHeader>
void Header<N_Size,  N_BusSize, N_MaxPktSize, N_MaxSuppHeaders, N_MaxPktId,
	T_HeaderLayout, T_DHeader>
	::StateTransition (const PacketDataType& PacketIn) {
#pragma HLS INLINE
#pragma HLS UNROLL
#pragma HLS LATENCY min=1 max=1

	typedef decltype(HeaderLayout.Key.front().KeyVal) KeyType;
	const KeyType DataInMask = (1 << HeaderLayout.KeyLocation.second) - 1;
	const auto tmpReceivedBits = receivedBits + N_BusSize;
	const KeyType tmpKeyVal =
		KeyType(PacketIn.Data >> stateTransShiftVal) & DataInMask;

	HeaderException = false;
	if (HeaderLayout.LastHeader) {
		IF_SOFTWARE(std::cout << "Last header. No state transition\n";)
		return;
	}

	// Looking at key position in the datastream
	if (!NextHeaderValid && tmpReceivedBits > HeaderLayout.KeyLocation.first) {
		HeaderException = true;
		// Checking for a match against the exected key
#define IMPL_RANGE_LOOP
#ifdef IMPL_RANGE_LOOP
		loop_key: for (const auto& key : HeaderLayout.Key) {
			if (key.KeyVal == tmpKeyVal & key.KeyMask) {
				IF_SOFTWARE(
				std::cout << "Found a valid transition from " <<	\
					instance_name << " to " << key.NextHeaderName << \
					". Key: " << std::hex << uint64_t(key.KeyVal) << '\n';
				)
				NextHeader = key.NextHeader;
				NextHeaderValid = true;
				HeaderException	= false;
			}
		}
#else
		loop_key: for (auto i = 0; i < HeaderLayout.Key.size(); ++i) {
			if (HeaderLayout.Key[i].KeyVal == tmpKeyVal & HeaderLayout.Key[i].KeyMask) {
				IF_SOFTWARE(
				std::cout << "Found a valid transition from " <<	\
					instance_name << " to " << HeaderLayout.Key[i].NextHeaderName << \
					". Key: " << std::hex << uint64_t(HeaderLayout.Key[i].KeyVal) << '\n';
				)
				NextHeader = HeaderLayout.Key[i].NextHeader;
				NextHeaderValid = true;
				HeaderException	= false;
			}
		}
#endif

		// Throws an error if key not found at the expected position
		IF_SOFTWARE(
		if (HeaderException)
			std::cout << "Header transition not found. Aborting processing\n";
		) // IF_SOFTWARE
	}
}

// Header extraction
template<uint16_t N_Size, uint16_t N_BusSize, uint16_t N_MaxPktSize,
	uint16_t N_MaxSuppHeaders, uint8_t N_MaxPktId, typename T_HeaderLayout,
	typename T_DHeader>
void Header<N_Size,  N_BusSize, N_MaxPktSize, N_MaxSuppHeaders, N_MaxPktId,
	T_HeaderLayout, T_DHeader>
	::ExtractFields(const PacketDataType& PacketIn, PHVDataType& PHV)
{
#pragma HLS INLINE
#pragma HLS LATENCY min=1 max=1
#pragma HLS ARRAY_PARTITION variable=shiftNumLookup dim=1

	const auto tmpLenVal = (PacketIn.Data >> headerLengthShiftVal) &
							((1 << HeaderLayout.HeaderLengthInd.second) - 1);
	const auto tmpReceivedBits = receivedBits + N_BusSize;
	ap_uint<numbits(HEADER_SIZE_IN_BITS)> tmpHeaderSize;

	if ((!headerSizeValid &&
		tmpReceivedBits > HeaderLayout.HeaderLengthInd.first) &&
		HeaderLayout.varSizeHeader) {
		HeaderLayout.getHeaderSize(tmpHeaderSize, tmpLenVal);
		IF_SOFTWARE(
		std::cout << "Header size of " << instance_name \
			<< " is " << tmpHeaderSize << '\n';
		)// IF_SOFTWARE
		headerSizeValid = true;
		headerSize = tmpHeaderSize;
		LenVal = tmpLenVal;
	}

	const auto tmpShiftVal = N_BusSize*(receivedWords+1);	//Implemented as SR not mul
	ExtractedHeaderType tmpDinlShifted;
#if LOOKUPTABLE_FOR_SHIFT_CALC
	if (HEADER_SIZE_IN_BITS == N_BusSize)
		tmpDinlShifted = PacketIn.Data;
	else
		tmpDinlShifted = ExtractedHeaderType(PacketIn.Data) <<
							shiftNumLookup[receivedWords];
#else
	if (HEADER_SIZE_IN_BITS == N_BusSize)
		tmpDinlShifted = PacketIn.Data;
	else
		tmpDinlShifted = (ExtractedHeaderType(PacketIn.Data) <<
							(HEADER_SIZE_IN_BITS - tmpShiftVal));
#endif
	ExtractedHeaderType tmpDinrShifted;
	if (HEADER_SIZE_IN_BITS <= N_BusSize)
		tmpDinrShifted = ExtractedHeaderType((PacketIn.Data) >>
							(N_BusSize - HEADER_SIZE_IN_BITS));

	IF_SOFTWARE(PHV.Name = instance_name;)
	PHV.ID = instance_id;
	PHV.PktID = PacketIn.ID;
	PHV.ValidPulse = HeaderDonePulse = false;

	// Performs header extraction till header done
	if (!HeaderDone) {
		PHV.ValidPulse = PHV.Valid = HeaderDone;
		if ((!HeaderLayout.varSizeHeader &&
			receivedWords < RECEIVED_MAX_WORDS) ||
			(HeaderLayout.varSizeHeader &&
			((!headerSizeValid && receivedBits < tmpHeaderSize) ||
			(headerSizeValid && receivedBits < headerSize)))) {
			// Saves logic if headers are not extracted
			if(!skipExtraction){
				if (HEADER_SIZE_IN_BITS > N_BusSize)
					ExtractedHeader |= tmpDinlShifted;
				else
					ExtractedHeader = tmpDinrShifted;
			}
		} else  {
			PHV.Data = (skipExtraction) ?
						ap_uint<bytes2Bits(N_Size)>(0) :
						(ExtractedHeader & HeaderLayout.PHVMask);
			PHV.ValidPulse = PHV.Valid = HeaderDone = HeaderDonePulse = true;
			PHV.ExtractedBitNum = headerSize;
			IF_SOFTWARE(
			std::cout << "Extracted: " << std::dec << \
				bits2Bytes(headerSize) << " Bytes. PHV: " << \
				std::hex << PHV.Data << '\n';
			) // IF_SOFTWARE
		}
	}
}

// Pipeline adjustment function for further stages
template<uint16_t N_Size, uint16_t N_BusSize, uint16_t N_MaxPktSize,
	uint16_t N_MaxSuppHeaders, uint8_t N_MaxPktId, typename T_HeaderLayout,
	typename T_DHeader>
void Header<N_Size,  N_BusSize, N_MaxPktSize, N_MaxSuppHeaders, N_MaxPktId,
	T_HeaderLayout, T_DHeader>
	::PipelineAdjust(const PacketDataType& PacketIn,
					 PacketDataType& PacketOut) {
#pragma HLS LATENCY min=1 max=1
#pragma HLS INLINE
#pragma HLS UNROLL
#pragma HLS ARRAY_PARTITION variable=HeaderLessBusStuffShift dim=1
#pragma HLS ARRAY_PARTITION variable=HeaderLessBusStuffRShift dim=1
#pragma HLS ARRAY_PARTITION variable=HeaderGreaterBusStuffShift dim=1
#pragma HLS ARRAY_PARTITION variable=HeaderGreaterBusStuffRShift dim=1
#pragma HLS ARRAY_PARTITION variable=HeaderBusCompVal dim=1

	// Call specific Pipeline adjust function
	// TODO: Ugly, solve the pointer reinterpret problem soon!!!
	//static_cast<T_DHeader>(*this).PipelineAdjustDer(PacketIn, PacketOut);
	auto derHeader = static_cast<T_DHeader>(*this);
	derHeader.PipelineAdjustDer(PacketIn, PacketOut);

	PacketOut.ID = PacketOutReg.ID;
	PacketOut.Start = HeaderDonePulse;
	PacketOut.Finish = PacketIn.Finish;
	PacketOut.HeaderID = NextHeader;

	IF_SOFTWARE(
	std::cout << instance_name << " Packet Start Out: " << std::hex << 		\
		PacketOut.Start << '\n';
	std::cout << instance_name << " Packet Finish Out: " << std::hex << 	\
		PacketOut.Finish << '\n';
	std::cout << instance_name << " Packet HeaderID Out: " << std::hex <<	\
		PacketOut.HeaderID << '\n';
	std::cout << instance_name << " Packet Word Out: " << std::hex << 		\
		PacketOut.Data << '\n';
	) // IF_SOFTWARE

	// Output data delay (to keep the pipeline full)
	PacketOutReg = PacketIn;
}

template<uint16_t N_Size, uint16_t N_BusSize, uint16_t N_MaxPktSize,
	uint16_t N_MaxSuppHeaders, uint8_t N_MaxPktId, typename T_HeaderLayout,
	typename T_DHeader>
void Header<N_Size,  N_BusSize, N_MaxPktSize, N_MaxSuppHeaders, N_MaxPktId,
	T_HeaderLayout, T_DHeader>
	::HeaderAnalysis(const PacketDataType& PacketIn, PHVDataType& PHV,
					 PacketDataType& PacketOut)
{
#pragma HLS LATENCY min=1 max=1
#pragma HLS PIPELINE II=1
#pragma HLS DEPENDENCE variable=HeaderIdle WAR false
#pragma HLS DEPENDENCE variable=NextHeaderValid WAR false
#pragma HLS DEPENDENCE variable=HeaderDone WAR false
#pragma HLS DEPENDENCE variable=NextHeader WAR false
#pragma HLS DEPENDENCE variable=HeaderDonePulse WAR false
#pragma HLS DEPENDENCE variable=headerSize WAR false
#pragma HLS DEPENDENCE variable=headerSizeValid WAR false

	// New packet detection
	if (PacketIn.Start && PacketIn.HeaderID == instance_id) {
		IF_SOFTWARE(std::cout << "Received a new packet" << '\n';)
		HeaderIdle = false;
	}

	IF_SOFTWARE(
	std::cout << instance_name << " Packet Start In: " << std::hex << 	\
		PacketIn.Start << '\n';
	std::cout << instance_name << " Packet Finish In: " << std::hex << 	\
		PacketIn.Finish << '\n';
	std::cout << instance_name << " Packet HeaderID In: " << std::hex <<\
		PacketIn.HeaderID << '\n';
	std::cout << instance_name << " Packet Word In: " << std::hex <<	\
		PacketIn.Data << '\n';
	) // IF_SOFTWARE

	if (!HeaderIdle) {

		// State transition evaluation
		StateTransition(PacketIn);

		// Header extraction
		ExtractFields(PacketIn, PHV);

		// Adjusting output data
		PipelineAdjust(PacketIn, PacketOut);

		// Execution control
		if (PacketIn.Finish /*|| HeaderException*/) {
			IF_SOFTWARE(std::cout << "Packet has finished\n";)
			HeaderIdle = true;
			receivedWords = 0;
			receivedBits = 0;
			NextHeaderValid = false;
			HeaderDone = false;
			NextHeader = 0;
			headerSizeValid = false;
			headerSize = HEADER_SIZE_IN_BITS;
		} else {
			++receivedWords;
			receivedBits+=N_BusSize;
		}
	} else {
#ifdef ENABLE_STATE_BYPASS
		PacketOut = PacketIn;
#endif
	}
}

// Derived Fixed Header
template<uint16_t N_Size, uint16_t N_BusSize, uint16_t N_MaxPktSize,
	uint16_t N_MaxSuppHeaders, uint8_t N_MaxPktId, typename T_HeaderLayout>
class FixedHeader : public Header <N_Size, N_BusSize, N_MaxPktSize,
	N_MaxSuppHeaders, N_MaxPktId, T_HeaderLayout,
	const FixedHeader<N_Size,  N_BusSize, N_MaxPktSize, N_MaxSuppHeaders,
		N_MaxPktId, T_HeaderLayout>&> {
	private:

		//User types
		typedef PacketData<N_BusSize, N_MaxSuppHeaders, N_MaxPktId>
			PacketDataType;
		typedef decltype(PacketDataType::Data) PktDbusType;
		typedef ap_uint<numbits(N_MaxSuppHeaders)> headerIDType;

	public:
		FixedHeader (IF_SOFTWARE(const std::string& instance_name,)
			const headerIDType& instance_id,
			const T_HeaderLayout& HLayout) :
			Header<N_Size, N_BusSize, N_MaxPktSize, N_MaxSuppHeaders,
				N_MaxPktId, T_HeaderLayout,//decltype(this)>
				const FixedHeader<N_Size, N_BusSize, N_MaxPktSize,
					N_MaxSuppHeaders, N_MaxPktId, T_HeaderLayout>&>
			(IF_SOFTWARE(instance_name,) instance_id, HLayout) // Header()
		{} // FixedHeader()

		void PipelineAdjustDer(const PacketDataType& PacketIn,
				PacketDataType& PacketOut) const {
#pragma HLS LATENCY min=0 max=0
#pragma HLS INLINE
			PacketOut.Data = (this->DATAOUT_STUFF_SHIFT == 0) ?
				PktDbusType(PacketIn.Data)
				: ((PktDbusType(this->PacketOutReg.Data) <<
					this->DATAOUT_STUFF_SHIFT) |
					(PktDbusType(PacketIn.Data) >> this->DATAOUT_STUFF_SIZE));
		}
};

template<uint16_t N_Size, uint16_t N_BusSize, uint16_t N_MaxPktSize,
	uint16_t N_MaxSuppHeaders, uint8_t N_MaxPktId, typename T_HeaderLayout>
class VariableHeader : public Header <N_Size, N_BusSize, N_MaxPktSize,
	N_MaxSuppHeaders, N_MaxPktId, T_HeaderLayout,
	const VariableHeader<N_Size,  N_BusSize, N_MaxPktSize, N_MaxSuppHeaders,
		N_MaxPktId, T_HeaderLayout>&> {
	private:

		// Constants
		static constexpr uint16_t ARR_LOOK_LEN_SIZE =
			std::tuple_size<decltype(T_HeaderLayout::ArrLenLookup)>::value;

		//User types
		typedef PacketData<N_BusSize, N_MaxSuppHeaders, N_MaxPktId>
			PacketDataType;
		typedef decltype(PacketDataType::Data) PktDbusType;
		typedef ap_uint<numbits(N_MaxSuppHeaders)> headerIDType;
		typedef std::array<ap_uint<numbits(N_BusSize)>, ARR_LOOK_LEN_SIZE>
			headerLenArrSizeType;

	public:

		VariableHeader (IF_SOFTWARE(const std::string& instance_name,)
			const headerIDType& instance_id,
			const T_HeaderLayout& HLayout) :
			Header<N_Size,  N_BusSize, N_MaxPktSize, N_MaxSuppHeaders,
				N_MaxPktId, T_HeaderLayout,//decltype(this)>
				const VariableHeader<N_Size, N_BusSize, N_MaxPktSize,
					N_MaxSuppHeaders, N_MaxPktId, T_HeaderLayout>&>
			(IF_SOFTWARE(instance_name,) instance_id, HLayout) // Header()
		{} // VariableHeader()

		void PipelineAdjustDer(const PacketDataType& PacketIn,
				PacketDataType& PacketOut) const {
#pragma HLS UNROLL
#pragma HLS LATENCY min=0 max=0
#pragma HLS INLINE

#if LOOKUPTABLE_FOR_OUT_BUS_SHIFT_CALC
			typedef std::array<PktDbusType, ARR_LOOK_LEN_SIZE> sArrType;
			sArrType DataHeaderLessBus;
			sArrType DataHeaderGreaterBus;
#pragma HLS ARRAY_PARTITION variable=DataHeaderGreaterBus dim=1
#pragma HLS ARRAY_PARTITION variable=DataHeaderLessBus dim=1

			for (size_t i = 0; i < ARR_LOOK_LEN_SIZE; ++i) {
				DataHeaderLessBus[i] =
					(PktDbusType(this->PacketOutReg.Data) <<
						this->HeaderLessBusStuffShift[i]) |
					(PktDbusType(PacketIn.Data) >>
						this->HeaderLessBusStuffRShift[i]);
				DataHeaderGreaterBus[i] =
					(PktDbusType(this->PacketOutReg.Data) <<
						this->HeaderGreaterBusStuffShift[i]) |
					(PktDbusType(PacketIn.Data) >>
						this->HeaderGreaterBusStuffRShift[i]);
			}

			const auto arrIdx = this->LenVal;
			if (this->HeaderBusCompVal[arrIdx])
				PacketOut.Data = DataHeaderLessBus[arrIdx];
			else
				PacketOut.Data = DataHeaderGreaterBus[arrIdx];
#else
			const ap_uint<N_BusSize> _busSizemod =
				this->busSizeMask & this->headerSize;
			ap_uint<N_BusSize> stuffShift;
			ap_uint<N_BusSize> stuffRShift;
			ap_uint<N_BusSize> stuffSizeMask;
			const auto comp_val = (this->headerSize >>
									this->BUS_SIZE_LENGTH) > 0;
			if (comp_val) {
				stuffShift = ap_uint<N_BusSize>(_busSizemod);
				stuffRShift = ap_uint<N_BusSize>(N_BusSize) -
								ap_uint<N_BusSize>(_busSizemod);
			} else {
				stuffShift = ap_uint<N_BusSize>(headerSize);
				stuffRShift = ap_uint<N_BusSize>(N_BusSize) -
								ap_uint<N_BusSize>(headerSize);
			}
				PacketOut.Data =
					(PktDbusType(this->PacketOutReg.Data) << stuffShift) |
					(PktDbusType(PacketIn.Data) >> stuffRShift);
#endif
		}
};
#endif //_PKT_HEADER_HPP_
