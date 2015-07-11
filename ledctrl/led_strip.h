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
  void initialize() const;

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
   * \brief Sets the color of the LED strip.
   * 
   * \param  red    the red component of the strip.
   * \param  green  the green component of the strip.
   * \param  blue   the blue component of the strip.
   */
  void setColor(u8 red, u8 green, u8 blue) const {
    analogWrite(m_redPin, red);
    analogWrite(m_greenPin, green);
    analogWrite(m_bluePin, blue);
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
  explicit LEDStripColorFader(const LEDStrip* ledStrip=0) : m_pLEDStrip(ledStrip) {}

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
