/**
 * \file types.h
 * \brief Declaration of some helper data types.
 */

#ifndef TYPES_H
#define TYPES_H

#ifdef __cplusplus
extern "C" {
#endif

#include <Arduino.h>
#include <stdint.h>

typedef int8_t s8;
typedef uint8_t u8;
#if defined(__unix__) || defined(__APPLE__)
typedef int16_t s16;
typedef uint16_t u16;
#endif

/**
 * Structure for storing a byte range.
 */
typedef struct {
  byte min;
  byte max;
} byte_range_t;

/**
 * Structure storing PWM limit voltages corresponding to the R, G, B and W pins of
 * a LED strip.
 */
typedef struct {
  byte_range_t red_duty_range;
  byte_range_t green_duty_range;
  byte_range_t blue_duty_range;
  byte_range_t white_duty_range;
} color_pwm_intervals_t;

#ifdef __cplusplus
}
#endif

#endif
