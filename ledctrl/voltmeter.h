/**
 * \file voltmeter.h
 * \brief Voltage meter class.
 */

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
   * Performs a measurement on the voltage meter and returns the measured value. 
   */
	float measure() {
    int value;
    float mod_duty;
    
    value = analogRead(m_pin);
    
#ifdef DEBUG
		Serial.print(" Voltage meter read raw value:");
		Serial.println(value);
#endif
    
		mod_duty = constrain(m_coefficient / (static_cast<float>(value) / 1023), 0, 1);
		if (fabs(mod_duty - m_lastReading) >= 0.05) {
			m_lastReading = mod_duty;
		}
   
		return m_lastReading;
	}
};

#endif
