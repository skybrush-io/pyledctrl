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

/**
 * \def DEBUG
 * 
 * Define this if you need debugging information on the serial console.
 */
#define DEBUG 1

/**
 * \def RED_PWM_PIN
 * 
 * Index of the PWM pin corresponding to the red LEDs.
 */
#define RED_PWM_PIN 5

/**
 * \def GREEN_PWM_PIN
 * 
 * Index of the PWM pin corresponding to the green LEDs.
 */
#define GREEN_PWM_PIN 6

/**
 * \def BLUE_PWM_PIN
 * 
 * Index of the PWM pin corresponding to the blue LEDs.
 */
#define BLUE_PWM_PIN 3

/**
 * \def MAIN_SWITCH
 * 
 * Analog input corresponding to the main switch.
 */
#define MAIN_SWITCH_PIN A5

/**
 * \def ENABLE_SERIAL_INPUT
 * 
 * Whether the LED controller should listen for incoming commands on the
 * serial port.
 */
// #define ENABLE_SERIAL_INPUT 1

/**
 * \def SERIAL_BAUD_RATE
 * 
 * Baud rate of the serial port where we will listen for incoming commands
 * and where we will send debug messages.
 */
#define SERIAL_BAUD_RATE 115200

/**
 * \def MAX_LOOP_DEPTH
 * 
 * Maximum number of nested loops that the command executor will be able to handle.
 */
#define MAX_LOOP_DEPTH 4

#ifdef __cplusplus
}
#endif

#endif
