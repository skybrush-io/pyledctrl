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
#define RED_PWM_PIN 6

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
#define BLUE_PWM_PIN 5

/**
 * \def MAIN_SWITCH_PIN
 * 
 * Analog input corresponding to the main switch.
 * If you have a switch-button, you should define this; otherwise comment this out.
 */
// #define MAIN_SWITCH_PIN A5

/**
 * \def ENABLE_SERIAL_INPUT
 * 
 * Whether the LED controller should listen for incoming commands on the
 * serial port.
 */
#define ENABLE_SERIAL_INPUT 1

/**
 * \def VOLTMETER_PIN
 * 
 * Index of the pin corresponding to the voltmeter. Comment this out if
 * you don't have a voltmeter.
 */
#define VOLTMETER_PIN 5

/**
 * \def VOLTMETER_ACCURACY
 *
 * Accuracy level for the voltmeter. This constant defines the number of
 * measurements to take on the voltmeter pin before a single measured
 * value is stored in our voltmeter class.
 */
#define VOLTMETER_ACCURACY 5

/**
 * \def LIGHT_COEFF
 * 
 * Correction coefficient for the LED brightness. Ignored if we have no voltmeter.
 */
#define LIGHT_COEFF 0.8

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

/**
 * \def MAX_TRIGGER_COUNT
 * 
 * Maximum number of triggers that the command executor will be able to handle.
 */
#define MAX_TRIGGER_COUNT 4

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
#define GREEN_LED_MAX_VOLTAGE 10.10

/**
 * \def BLUE_LED_MIN_VOLTAGE
 * Minimum (threshold) voltage where the blue LED opens 
 */
#define BLUE_LED_MIN_VOLTAGE 0.0

/**
 * \def BLUE_LED_MAX_VOLTAGE
 * Maximum voltage where the blue LED gives "quasi-white"
 */
#define BLUE_LED_MAX_VOLTAGE 9.10

#ifdef __cplusplus
}
#endif

#endif
