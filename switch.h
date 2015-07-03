/**
 * \file switch.h
 * \brief Implements a two-state switch attached to a pin.
 */

#ifndef SWITCH_H
#define SWITCH_H

#include <Arduino.h>
#include "types.h"

/**
 * \brief Implements a two-state switch attached to a pin.
 */
class Switch {
private:
  /**
   * The index of the pin that the switch is attached to.
   */
  u8 m_pin;

public:
  explicit Switch(u8 pin) : m_pin(pin) {
    pinMode(m_pin, INPUT);
  }

  /**
   * Returns whether the switch is on or off.
   */
  boolean on() const {
    return digitalRead(m_pin);
  }
};

#endif
