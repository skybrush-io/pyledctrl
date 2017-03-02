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

  /**
   * Time of last ON switch.
   */
   unsigned long m_LastSwitchOnTime;

  /**
   * Was there an off signal already? Otherwise we do not take into account
   * any on (avoiding situation when arduino os switched on later than
   * rc transmitter, which is already in on state */
  u8 m_EnableOn;

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
  void off(u8 enableOn = 1);

  /**
   * \brief Turns the pyro on to full.
   */
  void on();

  /**
   * \brief This function must be called repeatedly from the main loop
   *        of the sketch to keep the execution flowing.
   */
  void step();

private:

};

#endif
