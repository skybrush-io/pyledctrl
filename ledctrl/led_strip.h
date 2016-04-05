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
#include "config.h"
#include "types.h"
#include "utils.h"
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

  /**
   * Sets the color of the LED strip.
   *
   * \param  red    the red component of the strip.
   * \param  green  the green component of the strip.
   * \param  blue   the blue component of the strip.
   */
  void setColor(u8 red, u8 green, u8 blue) const {
    byte value;
    float compensator;

    compensator = m_pVoltmeter ? m_pVoltmeter->lastReading() : 1;

    // If the voltmeter measures zero or too high values, we skip compensation
    // altogether.
    if (compensator == 0 || compensator > 6)
      compensator = 1;

    // Calculate the linearized and voltage compensated lighting value that
    // will actually be written to the pin
    byte compensatedRed = calculateVoltageCompensatedValue(red,
                          m_pwmIntervals.red_duty_range, compensator);
	  LED_PIN_WRITE(m_redPin, compensatedRed);

    byte compensatedGreen = calculateVoltageCompensatedValue(green,
                            m_pwmIntervals.green_duty_range, compensator);
	  LED_PIN_WRITE(m_greenPin, compensatedGreen);

    byte compensatedBlue = calculateVoltageCompensatedValue(blue,
                           m_pwmIntervals.blue_duty_range, compensator);
	  LED_PIN_WRITE(m_bluePin, compensatedBlue);
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
   * \brief Helper function to compensate the non-linearity of the LED.
   *
   * May also perform additional compensation of voltage-related anomalies if
   * we have a voltmeter.
   *
   * \param  value        the RGB component to compensate
   * \param  range        range specifying the minimum and maximum voltages after
   *                      normalization
   * \param  compensator  compensation coefficient calculated by the voltmeter
   */
  u8 calculateVoltageCompensatedValue(u8 value, byte_range_t range, float compensator) const {
    float cubedValue = pow(static_cast<float>(value * compensator) / 255, 3);
    return static_cast<byte>(range.min + cubedValue * (range.max - range.min));
  }

  /**
   * \brief Calculates voltage compensation ranges for the three diodes (R, G and
   * B).
   *
   * This method is called once during initialization and it is not necessary
   * to call this manually.
   */
  void calculateVoltageCompensationRanges();

  /**
   * \brief Normalizes a voltage given as a floating point number between zero
   *        and the board's maximum input voltage to the range 0-254.
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
