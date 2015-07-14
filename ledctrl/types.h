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

/**
 * Structure for storing a byte range.
 */
typedef struct {
  byte min;
  byte max;
} byte_range_t;

/**
 * Structure storing PWM limit voltages corresponding to the R, G and B pins of
 * a LED strip.
 */
typedef struct {
  byte_range_t red_duty_range;
  byte_range_t green_duty_range;
  byte_range_t blue_duty_range;
} color_pwm_intervals_t;

#ifdef __cplusplus
}
#endif

#endif