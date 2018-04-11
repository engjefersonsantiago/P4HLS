/******************************************************************************
* Generic types and constants                                                 *
* Jeferson Santiago da Silva (eng.jefersonsantiago@gmail.com)                 *
******************************************************************************/
#include <features.h>
#include <cstdint>
#include <string>
#include <functional>
#include "ap_int.h"

#ifndef _DEF_TYPES_H_
#define _DEF_TYPES_H_

// Macro to remove non-synthesizable constructs
// Code from Francois-Raymond Boyer (francois-r.boyer@polymtl.ca)
#ifdef __SYNTHESIS__
	#define IF_SOFTWARE(...)
#else
	#define IF_SOFTWARE(...) __VA_ARGS__
#endif

//template<uint16_t Size>
//using n_uint = ap_uint<Size>;

//FIFO parameters
constexpr uint16_t MAX_PKT_SIZE = 1518;
constexpr uint16_t MIN_PKT_SIZE = 64;
constexpr uint16_t FIFO_ELEMENT_SIZE = 64;
constexpr uint16_t FIFO_SIZE = 4;     // Number of maximum sized packets

// FIFO basic element
template<typename T>
struct FifoElement
{
    T Element;
    bool PacketIni;
    bool PacketEnd;
    FifoElement() : PacketIni{false}, PacketEnd{false}, Element{} {}
};

// Workaround non constexpr log and ceil
// Reference: https://hbfs.wordpress.com/2016/03/22/log2-with-c-metaprogramming/
template<typename T>
constexpr T numbits(T n) {
	return ((n<2) ? 1 : 1+numbits(n>>1));
}

template<typename T_a, typename T_b>
constexpr T_a mod(T_a a, T_b b) {
	return (a<b) ? a : mod(a-b, b);
}

template<typename T_a, typename T_b>
constexpr T_a DivAndCeil(T_a a, T_b b) {
	return (a%b == 0 ? a/b : (a/b + 1));
}

template<typename T>
constexpr T bytes2Bits (T a) {
	return a<<3;
}

template<typename T>
constexpr T bits2Bytes (T a) {
	return a>>3;
}

template<typename T>
constexpr T max (T a, T b){
	return ((a > b) ? a : b);
}

template<typename T>
constexpr T min (T a, T b){
	return ((a < b) ? a : b);
}

// Calculates the necessary bit stuff for a bus
// For two elements, do C = A
static constexpr uint16_t bus_stuff_wraparound (
	uint16_t A, uint16_t B, uint16_t C) {
	return (((A) < (B)) ? (B - C) : (B - (C%B)));
}

// Init array function
template<typename T_class, uint16_t N_ID, typename T, typename F>
const T init_array(const F& f) {
	typename std::remove_cv<T>::type arr {};
	for (size_t i = 0; i < arr.size(); ++i)
		arr[i] = f(i);
	return arr;
}

// Init array function
template<typename T_class, uint16_t N_ID, typename T>
const T init_array_fun(const std::function<typename T::value_type(size_t)>& f) {
	typename std::remove_cv<T>::type arr {};
	for (size_t i = 0; i < arr.size(); ++i)
		arr[i] = f(i);
	return arr;
}

#endif //_DEF_TYPES_H_
