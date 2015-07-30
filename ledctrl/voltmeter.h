/**
* \file voltmeter.h
* \brief Voltage meter class.
*/

#ifndef VOLTMETER_H
#define VOLTMETER_H

#include "config.h"
#include <Arduino.h>
#include <math.h>

/**
 * Class that represents a voltage meter.
 */
class VoltMeter {

private:
	/**
	 * Index of the pin on which the voltmeter measurement can be read.
	 */
	u8 m_pin;

	/**
	 * Correction coefficient to use on the voltmeter readings.
	 */
	float m_coefficient;

	/**
	 * Storage for the last measured value to implement a simple noise filtering.
	 */
	float m_lastReading;

public:
	/**
	* Constructor.
	*
	* \param  pin  index of the pin on which the voltmeter measurement can be read.
	* \param  coefficient  correction coefficient to use on the voltmeter readings
	*/
	explicit VoltMeter(u8 pin, float coefficient)
		: m_pin(pin), m_coefficient(coefficient), m_lastReading(0.0) {}

	/**
	* Returns the last voltage reading of the voltage meter.
	*/
	float lastReading() const {
		return m_lastReading;
	}

	/**
	* Performs a measurement on the voltage meter.
	* Returns a coefficient measured, scaled value
	* if which is multiply the desired lighting, compensate the decreasing or increasing of voltage
	* This function can compensate in around half of full interval
	*/
	float measure() {
		int unscaled_reading = readUnscaledValue();
		float compensator;

		#ifdef DEBUG
		// Serial.print(" Voltage meter read raw value:");
		// Serial.println(unscaled_reading);
		#endif

		compensator = constrain(m_coefficient / (static_cast<float>(unscaled_reading) / 1023), 0, 1);
		if (fabs(compensator - m_lastReading) <= 0.05) {
			m_lastReading = compensator;
		}
		return m_lastReading;
	}

	/**
	 * \brief Reads an unscaled voltage measure from the voltmeter pin,
	 *        optionally performing some black magic with multiple readings to
	 *        return a voltage reading with increased accuracy.
	 *
	 * \return An unscaled voltage measure
	 */
	int readUnscaledValue() {
#if VOLTMETER_ACCURACY > 1
		float curr_reading, prev_reading;
		float sum_readings = 0.0;
		byte i, num_readings;

		prev_reading = analogRead(m_pin);
		num_readings = 1;
		sum_readings = prev_reading;
		for (i = 1; i < VOLTMETER_ACCURACY; i++) {
			curr_reading = analogRead(m_pin);
			if (fabs(curr_reading - prev_reading) < 2) {
				num_readings++;
				sum_readings += curr_reading;
			}
			prev_reading = curr_reading;
		}

		return sum_readings / num_readings;
#else
		return analogRead(m_pin);
#endif
	}
};

#endif
