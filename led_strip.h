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
   * \brief Sets the color of the LED strip to a gray shade.
   * 
   * \param  gray   the shade of gray (0=black, 255=white).
   */
  void setGray(u8 gray) const {
    setColor(gray, gray, gray);
  }
};

#endif
