/**
 * \file types.h
 * \brief Declaration of some helper data types.
 */

#ifndef TYPES_H
#define TYPES_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>

typedef uint8_t u8;


#ifdef __cplusplus

typedef struct
{
	byte R_duty_min;
	byte G_duty_min;
	byte B_duty_min;
	byte R_duty_max;
	byte G_duty_max;
	byte B_duty_max;
} colorPWMintervals;
}

#endif

#endif
