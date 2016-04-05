/**
 * \file utils.h
 * \brief Utility functions and macros that do not fit elsewhere
 */

#ifndef UTILS_H
#define UTILS_H

#include <Arduino.h>
#include "config.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * \def LED_PIN_WRITE
 * \brief Writes a value in the range 0-255 (inclusive) to the given LED pin.
 *
 * This macro takes into account the polarity and max PWM value of the pins on
 * the board.
 */
#ifdef ENABLE_IS_LOW
#  define LED_PIN_WRITE(pin, value) analogWrite(pin, 255-(MAX_PWM * value / 255))
#else
#  define LED_PIN_WRITE(pin, value) analogWrite(pin, MAX_PWM * value / 255)
#endif

#ifdef __cplusplus
}
#endif

#endif
