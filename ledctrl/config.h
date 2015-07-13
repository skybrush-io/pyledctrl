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
#define BLUE_PWM_PIN 9

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

#define VOLTMETER_PIN 5

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

#define MAINSWITCH 0
	/**
	* \def MAINSWITCH
	* If you have an switch-button, you should define this.
	*/



#if ITNUM == 0 //number of interrupt
#define ITPIN 2 //PIN of Interrupt
#elif ITNUM == 1
#define ITPIN 3
#endif

	/*
	* define interrupts
	*/
#define PWM_INTERRUPT 1
#define PPM_INTERRUPT 0


#define ITNUM 1
	/**
	* \def ITNUM
	* Number of interrapt. (0 or 1)
	* Arduino Nano has two IT pins.
	* Interrupt 0 is on digital pin 2, IT1 is on D2
	*/
#if ITNUM == 0 //number of interrupt
#define ITPIN 2 //PIN of Interrupt
#elif ITNUM == 1
#define ITPIN 3
#endif

	/*

	/*
	* Define the significant voltage values,
	* - maximum input voltage on the board
	* - minimum voltage where opens diodes
	* - maximum voltages where diodes give "quasi-white"
	*/
#define MAXVOLTAGE 12.00
#define MAXVOLTAGE_RED 12.00
#define MAXVOLTAGE_GREEN 10.10
#define MAXVOLTAGE_BLUE 9.10
#define MINVOLTAGE_RED 0
#define MINVOLTAGE_GREEN 0
#define MINVOLTAGE_BLUE 0


#ifdef __cplusplus
}
#endif

#endif