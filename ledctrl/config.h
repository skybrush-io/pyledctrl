/**
 * \file config.h
 * \brief Configuration constants for the LED controller project.
 */

#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ************************************************************************** */
/* Basic settings                                                             */
/* ************************************************************************** */

/**
 * Use only one from the following definitions to define board version
 * NANOLED_VERSION = 1 corresponds to version v1.0
 * NANOLED_VERSION = 2 corresponds to versions 2.0 and 2.1
 */
#define NANOLED_VERSION 1

/**
 * \def ENABLE_IS_LOW
 *
 * Define if enable of LED is at LOW/zero PWM (NanoLED v2.0 based on XL4001)
 * Do not define if it is at HIGH/max PWM (NanoLED v1.0 based on pure led strip)
 */
#if NANOLED_VERSION == 2
#  define ENABLE_IS_LOW
#endif

/**
 * \def DEBUG
 *
 * Define this if you need debugging information on the serial console.
 */
// #define DEBUG 1

/**
 * \def set to 1 if you want to use white LED in the color mixing, 0 if not
 */
#define USE_WHITE_LED 0

/**
 * \def MAX_PWM
 *
 * With this macro we can downscale all raw outputs to e.g. avoid overheating
 * of the module.
 */
#define MAX_PWM 255

/**
 * \def CLOCK_SKEW_CALIBRATION
 * 
 * Define this macro if you want to calibrate the clock skew of the NanoLED
 * board so it can compensate for inaccuracies in the clock rate when playing
 * back a preprogrammed light sequence.
 *
 * If this macro is not defined, the board will attempt to read a previously
 * stored calibration value from EEPROM. In the absence of such a calibration
 * value, it will assume that the clock rate is perfectly aligned with wall
 * clock time (there is no skew between them). If a calibration value is found,
 * it is assumed that X milliseconds in wall clock time is X*C milliseconds
 * on the Arduino's clock, where C is the calibration value.
 *
 * If this macro is defined, the board will check the elapsed time on its internal
 * clock when the main switch is turned off. If the elapsed time is between
 * 95% and 105% of the value of the macro \c CLOCK_SKEW_CALIBRATION_DURATION_IN_MINUTES
 * it will assume that the main switch was turned off exactly at the time specified in
 * that macro and update the calibration value in the EEPROM accordingly.
 */
// #define CLOCK_SKEW_CALIBRATION 1

/**
 * \def CLOCK_SKEW_CALIBRATION_DURATION_IN_MINUTES
 *
 * Length of the clock skew calibration in wall clock time in minutes. When doing
 * the calibration, you are expected to turn off the main switch exactly at this
 * number of minutes.
 */
#define CLOCK_SKEW_CALIBRATION_DURATION_IN_MINUTES 10

/* ************************************************************************** */
/* Pin configurations                                                         */
/* ************************************************************************** */

/**
 * \def PYRO_PIN
 *
 * Define the pin to use as pyro output. Make sure it does not overlap with
 * any of the LED output pins.
 */
//#define PYRO_PIN 6

/**
 * \def RED_PWM_PIN
 *
 * Index of the PWM pin corresponding to the red LEDs.
 */
#if NANOLED_VERSION == 2
#  define RED_PWM_PIN 11 // timer2 (NanoLED v2.1)
#else
#  if PYRO_PIN == 6
#    define RED_PWM_PIN 7 // NanoLED v1.0 dummy red pin, 6 used for pyro
#  else
#    define RED_PWM_PIN 6 // NanoLED v1.0
#  endif
#endif

/**
 * \def GREEN_PWM_PIN
 *
 * Index of the PWM pin corresponding to the green LEDs.
 */
#define GREEN_PWM_PIN 9

/**
 * \def BLUE_PWM_PIN
 *
 * Index of the PWM pin corresponding to the blue LEDs.
 */
#if NANOLED_VERSION == 2
#  define BLUE_PWM_PIN 3 // timer2 (NanoLED v2.1)
#else
#  define BLUE_PWM_PIN 5 // NanoLED v1.0
#endif

/**
 * \def WHITE_PWM_PIN
 *
 * Index of the PWM pin corresponding to the WHITE LEDs.
 * If you have no white LED, set it to zero.
 */
#define WHITE_PWM_PIN 10

/**
 * \def MAIN_SWITCH_PIN
 *
 * Analog input corresponding to the main switch.
 * If you have a switch-button, you should define this; otherwise comment this out.
 */
//#define MAIN_SWITCH_PIN A5

/* ************************************************************************** */
/* RC channel configuration
/* ************************************************************************** */

/**
 * \def MAIN_SWITCH_CHANNEL
 *
 * Zero-indexed RC channel corresponding to the main switch
 * Comment this out if you do not want to have
 * an RC channel associated with a main switch
 */
#define MAIN_SWITCH_CHANNEL 6

/**
 * \def LANDING_SWITCH_CHANNEL
 *
 * Zero-indexed RC channel corresponding to the landing switch
 * Comment this out if you do not want to have
 * an RC channel associated with a landing switch
 */
//#define LANDING_SWITCH_CHANNEL 5

/**
 * \def BYTECODE_RC_CHANNEL
 *
 * Zero-indexed RC channel corresponding to the bytecode_rc mode (color selection through
 * rc sticks). Comment this out if you do not want to have
 * an RC channel associated with a bytecode_rc mode
 */
#define BYTECODE_RC_CHANNEL 4

/**
 * \def PYRO_SWITCH_CHANNEL
 *
 * Zero-indexed RC channel that triggers the pyro
 */
//#define PYRO_SWITCH_CHANNEL 7


/* ************************************************************************** */
/* Serial port configuration                                                  */
/* ************************************************************************** */

/**
 * \def ENABLE_SERIAL_INPUT
 *
 * Whether the LED controller should listen for incoming commands on the
 * serial port.
 */
#define ENABLE_SERIAL_INPUT 1

/**
* \def ENABLE_STARTUP_SIGNAL
 * 
 * When this macro is defined, the LED controller will first wait for the
 * string "?READY?" followed by a newline character on the serial console
 * before it will enter the main loop or parse any other serial input.
 */
#define ENABLE_SERIAL_PORT_STARTUP_SIGNAL 1

/**
 * \def SERIAL_BAUD_RATE
 *
 * Baud rate of the serial port where we will listen for incoming commands
 * and where we will send debug messages.
 */
#define SERIAL_BAUD_RATE 115200

/* ************************************************************************** */
/* Voltage levels and voltmeter configuration                                 */
/* ************************************************************************** */

/**
 * \def BOARD_MAX_INPUT_VOLTAGE
 * Maximum input voltage on the board.
 */
#define BOARD_MAX_INPUT_VOLTAGE 12.00

/**
 * \def RED_LED_MIN_VOLTAGE
 * Minimum (threshold) voltage where the red LED opens
 */
#define RED_LED_MIN_VOLTAGE 0.0

/**
 * \def RED_LED_MAX_VOLTAGE
 * Maximum voltage where the red LED gives "quasi-white"
 */
#define RED_LED_MAX_VOLTAGE 12.00

/**
 * \def GREEN_LED_MIN_VOLTAGE
 * Minimum (threshold) voltage where the green LED opens
 */
#define GREEN_LED_MIN_VOLTAGE 0.0

/**
 * \def GREEN_LED_MAX_VOLTAGE
 * Maximum voltage where the green LED gives "quasi-white"
 */
//#define GREEN_LED_MAX_VOLTAGE 10.10
#define GREEN_LED_MAX_VOLTAGE 12.00

/**
 * \def BLUE_LED_MIN_VOLTAGE
 * Minimum (threshold) voltage where the blue LED opens
 */
#define BLUE_LED_MIN_VOLTAGE 0.0

/**
 * \def BLUE_LED_MAX_VOLTAGE
 * Maximum voltage where the blue LED gives "quasi-white"
 */
//#define BLUE_LED_MAX_VOLTAGE 9.10
#define BLUE_LED_MAX_VOLTAGE 12.00

/**
 * \def WHITE_LED_MIN_VOLTAGE
 * Minimum (threshold) voltage where the white LED opens
 */
#define WHITE_LED_MIN_VOLTAGE 0.0

/**
 * \def WHITE_LED_MAX_VOLTAGE
 * Maximum voltage where the white LED gives "quasi-white"
 */
#define WHITE_LED_MAX_VOLTAGE 12.00

/**
 * \def VOLTMETER_PIN
 *
 * Index of the pin corresponding to the voltmeter. Comment this out if
 * you don't have a voltmeter.
 */
// #define VOLTMETER_PIN 5

/**
 * \def VOLTMETER_ACCURACY
 *
 * Accuracy level for the voltmeter. This constant defines the number of
 * measurements to take on the voltmeter pin before a single measured
 * value is stored in our voltmeter class.
 */
//#define VOLTMETER_ACCURACY 5

/**
 * \def LIGHT_COEFF
 *
 * Correction coefficient for the LED brightness. Ignored if we have no voltmeter.
 */
//#define LIGHT_COEFF 0.8

/* ************************************************************************** */
/* Bytecode executor configuration                                            */
/* ************************************************************************** */

/**
 * \def MAX_LOOP_DEPTH
 *
 * Maximum number of nested loops that the command executor will be able to handle.
 */
#define MAX_LOOP_DEPTH 4

/**
 * \def MAX_TRIGGER_COUNT
 *
 * Maximum number of triggers that the command executor will be able to handle.
 */
#define MAX_TRIGGER_COUNT 4

/* ************************************************************************** */
/* Remote controller configuration                                            */
/* ************************************************************************** */

/**
 * \def USE_PPM_REMOTE_CONTROLLER
 * Define this to 1 if you want to read PPM encoded signals from an RC controller.
 */
#define USE_PPM_REMOTE_CONTROLLER 1

/**
 * \def USE_PWM_REMOTE_CONTROLLER
 * Define this to 1 if you want to read PWM encoded signals from an RC controller.
 */
#define USE_PWM_REMOTE_CONTROLLER 0

/**
 * \def RC_INTERRUPT
 * Define this to the index of the interrupt to use for reading the RC controller
 * signal.
 *
 * The Arduino Nano has two interrupt pins; interrupt 0 is on digital pin 2,
 * while interrupt 1 is on digital pin 3.
 */
#define RC_INTERRUPT 0

#ifdef __cplusplus
}
#endif

#endif
