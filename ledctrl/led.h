/**
 * \file led.h
 * \brief Handling of a single-coloured LED attached to the Arduino.
 */

#ifndef LED_H
#define LED_H

#include <Arduino.h>
#include "types.h"
#include "utils.h"

/**
 * \brief Represents a single LED attached to the Arduino on a given pin.
 */
class LED {
private:
  /**
   * Index of the pin of the LED.
   */
  u8 m_pin;

public:
  explicit LED(u8 pin=LED_BUILTIN) : m_pin(pin) {
    initialize();
  }

  /**
   * \brief Initializes the LED.
   * 
   * Called automatically by the constructor; no need to call it explicitly.
   */
  void initialize() const {
    pinMode(m_pin, OUTPUT);
    off();
  }

  /**
   * Turns the LED off.
   */
  void off() const {
    setBrightness(0);
  }

  /**
   * Turns the LED on (full brightness).
   */
  void on() const {
    setBrightness(255);
  }

  /**
   * Sets the brightness of the LED. Intermediate values work only for
   * PWM pins.
   */
  void setBrightness(u8 level) const {
	  LED_PIN_WRITE(m_pin, level);
  }
};

#endif

