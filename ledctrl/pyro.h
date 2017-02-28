/**
 * \file pyro.h
 * \brief Handling of a single pyro trigger attached to the Arduino.
 *
 * It is assumed that the pyro pin is configured in \c config.h.
 */

#ifndef PYRO_H
#define PYRO_H

#include <Arduino.h>
#include <assert.h>
#include "config.h"
#include "types.h"
#include "utils.h"

/**
* \brief Represents an RGB LED strip attached to the Arduino on three pins,
*        one for each channel.
*/
class Pyro {
private:
  /**
   * Index of the pyro pin.
   */
  u8 m_Pin;

public:

  /**
   * Constructs a LED strip that uses the given pins.
   *
   * \param  pyroPin    index of the pyro pin
   */
  Pyro(u8 pyroPin)
    : m_Pin(pyroPin) {
    initialize();
  }

  /**
   * \brief Initializes the Pyro trigger.
   *
   * Called automatically by the constructor; no need to call it explicitly.
   */
  void initialize();

  /**
   * \brief Turns the pyro off.
   */
  void off() const {
    LED_PIN_WRITE(m_Pin, 0);
  }

  /**
   * \brief Turns the pyro on to full.
   */
  void on() const {
    LED_PIN_WRITE(m_Pin, 255);
  }

private:

};

#endif
