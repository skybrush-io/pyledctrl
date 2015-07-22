/**
* \file led_strip.h
* \brief Handling of a single LED strip attached to the Arduino.
*
* It is assumed that the red, green and blue components of the LED
* strip are controlled via three PWM pins, and the indices of these
* pins are configured in \c config.h.
*/

#ifndef LED_STRIP_H
#define LED_STRIP_H

#include <Arduino.h>
#include <assert.h>
#include "colors.h"
#include "types.h"
#include "config.h"
#include "voltmeter.h"


/**
* \brief Represents an RGB LED strip attached to the Arduino on three pins,
*        one for each channel.
*/
class LEDStrip {
private:
	/**
	* Index of the red pin of the LED strip.
	*/
	u8 m_redPin;

	/**
	* Index of the green pin of the LED strip.
	*/
	u8 m_greenPin;

	/**
	* Index of the blue pin of the LED strip.
	*/
	u8 m_bluePin;

	/**
	* Pointer to an optional voltage meter that the LED strip may use for non-linear
	* brightness compensation.
	*/
	VoltMeter* m_pVoltmeter;

	/**
	* Structure that stores voltage limits for the PWM pins so we could compensate
	* non-linearly to make the LED brightness change in a linear manner.
	*/
	color_pwm_intervals_t m_pwmIntervals;




public:

	/**
	* Constructs a LED strip that uses the given pins.
	*
	* \param  redPin    index of the red pin
	* \param  greenPin  index of the green pin
	* \param  bluePin   index of the blue pin
	*/
	LEDStrip(u8 redPin, u8 greenPin, u8 bluePin)
		: m_redPin(redPin), m_greenPin(greenPin), m_bluePin(bluePin) {
		initialize();
	}

	/**
	* \brief Initializes the LED strip.
	*
	* Called automatically by the constructor; no need to call it explicitly.
	*/
	void initialize();

	/**
	* \brief Turns the LED strip off.
	*/
	void off() const {
		setGray(0);
	}

	/**
	* \brief Turns the LED strip on to full brightness.
	*/
	void on() const {
		setGray(255);
	}

	/*
	* function for calculating ranges of colours
	*/

	void CalculateRanges()
	{
		m_pwmIntervals.red_duty_range.min = normalizeVoltage(RED_LED_MIN_VOLTAGE);
		m_pwmIntervals.red_duty_range.max = normalizeVoltage(RED_LED_MAX_VOLTAGE);
		m_pwmIntervals.green_duty_range.min = normalizeVoltage(GREEN_LED_MIN_VOLTAGE);
		m_pwmIntervals.green_duty_range.max = normalizeVoltage(GREEN_LED_MAX_VOLTAGE);
		m_pwmIntervals.blue_duty_range.min = normalizeVoltage(BLUE_LED_MIN_VOLTAGE);
		m_pwmIntervals.blue_duty_range.max = normalizeVoltage(BLUE_LED_MAX_VOLTAGE);
	}

	/*
	* function for normalize voltages to maximum input voltage in board
	*/
	byte normalizeVoltage(float voltage) {
		return static_cast<byte>(254 * voltage / BOARD_MAX_INPUT_VOLTAGE);
	}

	/*
	* function for setting up the colours on the RGB LED strip 
	*/
	void setColor(u8 red, u8 green, u8 blue) const {
		byte value;
		static float compensator;
		
		compensator = m_pVoltmeter->lastReading();

		// if voltmeter measure zero values or too high values, the compensator will be one,
		// thus we do not compensate (we multiply the lighting value with one. )
		if (compensator == 0 || compensator > 6)
			compensator = 1;

		//calculating the linearized and voltage compensated lighting value, which is will be sended
		byte R = calculateVoltageCompensatedValue(red, m_pwmIntervals.red_duty_range, compensator);
		#if DEBUG
		Serial.print(" R: "); Serial.print(red);
		#endif
		analogWrite(m_redPin, R);

		byte G = calculateVoltageCompensatedValue(green, m_pwmIntervals.green_duty_range, compensator);
		#if DEBUG
		Serial.print(" G: "); Serial.print(G);
		#endif
		analogWrite(m_greenPin, G);

		byte B = calculateVoltageCompensatedValue(blue, m_pwmIntervals.blue_duty_range, compensator);
		#if DEBUG
		Serial.print(" B: "); Serial.print(B); Serial.println();
		#endif
		analogWrite(m_bluePin, B);

	}

	/**
	* \brief Sets the color of the LED strip.
	*
	* \param  color    the desired color of the strip.
	*/
	void setColor(rgb_color_t color) const {
		setColor(color.red, color.green, color.blue);
	}

	/**
	* \brief Sets the color of the LED strip to a gray shade.
	*
	* \param  gray   the shade of gray (0=black, 255=white).
	*/
	void setGray(u8 gray) const {
		setColor(gray, gray, gray);
	}

	/**
	* \brief Attaches a voltage meter to the LED strip for brightness compensation.
	*/
	void setVoltmeter(VoltMeter* voltmeter) {
		m_pVoltmeter = voltmeter;
	}

private:
	/**
	*
	* We must compensate the LED's non-linearity and if we have an voltmeter, we can compensate some voltage anomaly
	*
	* \param  value    the RGB component to compensate
	* \param  range    range specifying the minimum and maximum voltages after normalization
	* \param  compensator  a coefficient, which is calculated by voltmeter
	*/
	u8 calculateVoltageCompensatedValue(u8 value, byte_range_t range, float compensator) const {
		float cubedValue = pow(static_cast<float>(value * compensator) / 255, 3);
		return static_cast<byte>(range.min + cubedValue * (range.max - range.min));
	}

	/**
	* Normalizes a voltage given as a floating point number between zero and the board's
	* maximum input voltage to the range 0-254.
	*/
	byte normalizeVoltage(float voltage) const;
};

/**
* \brief Color fader for a LED strip.
*
* This object provides a function-like interface that accepts a
* single floating-point number between 0 and 1 and sets the color
* of the LED strip to a linearly interpolated one between a given
* start and end color.
*/
class LEDStripColorFader {
private:
	/**
	* The LED strip that the fader controls.
	*/
	const LEDStrip* m_pLEDStrip;

public:
	/**
	* The start color.
	*/
	rgb_color_t startColor;

	/**
	* The end color.
	*/
	rgb_color_t endColor;

public:
	/**
	* Constructor.
	*
	* \param  ledStrip  the LED strip that the fader will control
	*/
	explicit LEDStripColorFader(const LEDStrip* ledStrip = 0) : m_pLEDStrip(ledStrip) {}

	/**
	* Returns the LED strip that the fader will control.
	*/
	const LEDStrip* ledStrip() const {
		return m_pLEDStrip;
	}

	/**
	* Sets the LED strip that the fader will control.
	*/
	void setLEDStrip(const LEDStrip* value) {
		m_pLEDStrip = value;
	}

	/**
	* Fades the LED strip to the given interpolation value.
	*/
	void operator()(float value) const {
		assert(m_pLEDStrip != 0);
		m_pLEDStrip->setColor(rgb_color_linear_interpolation(startColor, endColor, value));
	}
};

#endif
