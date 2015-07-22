/**
* \file voltmeter.h
* \brief Voltage meter class.
*/
#define INCREASEACCURACY 1
#ifdef INCREASEACCURACY
#define ACCURACY 5
#endif


#ifndef VOLTMETER_H
#define VOLTMETER_H

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
	/*
	* readed value of analog input. This is unscaled and non-usable like this
	*/
	int readed_value;

	/*
	* vector of valided values
	*/
	float valided[ACCURACY];
	/*
	* calculated accurate voltage
	*/
	float accurate_value;

	/*
	* the calculated value, which is usable for compensate lighting
	*/
	float compensator;
	/*
	* temp values for function of increasing accuracy
	*/
	byte i = 1;
	byte validednum = 1;

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
	float measure()
	{
		#if INCREASEACCURACY
		readed_value = read_Accurate();
		#elif INCREASEACCURACY == 0
		readed_value = analogRead(m_pin);
		#endif

		#ifdef DEBUG
		Serial.print(" Voltage meter read raw value:");
		Serial.println(readed_value);
		#endif

		compensator = constrain(m_coefficient / (static_cast<float>(readed_value) / 1023), 0, 1);
		if (fabs(compensator - m_lastReading) <= 0.05) {
			m_lastReading = compensator;
		}
		//Serial.println(m_lastReading);
		return m_lastReading;
	}

	/*
	* function for reading more sample and increase accuracy with this
	*/

	int read_Accurate()
	{
		valided[0] = analogRead(m_pin);
		i = 1;
		validednum = 1;
		while (i < ACCURACY)
		{
			valided[i] = analogRead(m_pin);
			if (abs(valided[i] - valided[i - 1]) < 2)
			{
				validednum++;
				accurate_value += valided[i];
			}
			i++;
		}
		return accurate_value /= validednum;
	}
};

#endif
