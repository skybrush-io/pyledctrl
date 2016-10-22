/**
 * \file calibration.h
 * \brief Functions and classes for calibrating the clock skew of the Arduino.
 */

#ifndef CALIBRATION_H
#define CALIBRATION_H

#include <Arduino.h>
#include "led_strip.h"

/**
 * Struct that is formatted in the way the calibration data should be laid out
 * in the EEPROM.
 */
typedef struct {
  
  /**
   * Magic bytes that allow us to identify whether there is a calibration data
   * at the beginning of the EEPROM or not. These bytes must be equal to
   * \ref CALIBRATION_MAGIC_BYTES in order for the calibration data to be valid.
   */
  uint32_t magicBytes;
   
  /**
   * The compensation factor for the clock skew of the Arduino. This means that
   * when X milliseconds passes in wall clock time, the Arduino's clock will be
   * advanced by X*C milliseconds where C is the clock skew compensation factor.
   */
  float clockSkewCompensationFactor;
  
} calibration_data_t;

/**
 * Returns a calibration data object that represents a completely uncalibrated
 * state.
 *
 * \param  data  the calibration data struct to return the result into
 */
void assumeUncalibratedState(calibration_data_t* data);

/**
 * Finishes the calibration by indicating that the calibration duration given in
 * wall clock time in \c CLOCK_SKEW_CALIBRATION_DURATION_IN_MINUTES took the
 * given number of milliseconds on the Arduino's clock.
 *
 * \param  time  the duration on the Arduino's clock corresponding to
 *         \c CLOCK_SKEW_CALIBRATION_DURATION_IN_MINUTES in wall clock time
 * \param  pLedStrip  pointer to an optional LED strip that will be flashed
 *         three times in green if the calibration was successful or three times
 *         in red if the calibration failed.
 * \return the new calibration factor or zero if the calibration failed
 */
float finishCalibrationWithDuration(unsigned long time, LEDStrip* pLedStrip = 0);

/**
 * Reads the calibration data from the EEPROM.
 *
 * When the EEPROM does not contain valid calibration data, this function will
 * return \c false and copy the default calibration data that assumes no clock
 * skew into \ref data.
 * 
 * \param  data  the calibration data struct to read the calibration data into
 *         from the EEPROM
 * \return whether the calibration data was loaded successfully
 */
bool readCalibrationData(calibration_data_t* data);

/**
 * Resets the calibration data written into the EEPROM.
 */
void resetCalibrationData();

/**
 * Writes the given calibration data to the EEPROM.
 *
 * \param  data  the calibration data to write
 */
void writeCalibrationData(calibration_data_t* data);

#endif
