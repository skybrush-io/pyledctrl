#include <Arduino.h>
#include <avr/eeprom.h>
#include "calibration.h"
#include "config.h"
#include "led_strip.h"

/**
 * The magic bytes that we expect to find at the beginning of the EEPROM if the
 * calibration data is valid.
 */
const uint32_t CALIBRATION_MAGIC_BYTES = 0xDEADBEEF;

void assumeUncalibratedState(calibration_data_t* data) {
  data->magicBytes = CALIBRATION_MAGIC_BYTES;
  data->clockSkewCompensationFactor = 1.0;
}

float finishCalibrationWithDuration(unsigned long time, LEDStrip* pLedStrip) {
  calibration_data_t calibration;
  float factor = (CLOCK_SKEW_CALIBRATION_DURATION_IN_MINUTES * 60000.0) / time;
  rgb_color_t color = { 0, 0, 0 };

  if (factor >= 0.95 && factor <= 1.05) {
    calibration.clockSkewCompensationFactor = factor;
    writeCalibrationData(&calibration);
  } else {
    factor = 0;
  }
  
  if (factor > 0) {
    // Flash green color three times to indicate success
    color.green = 255;
  } else {
    // Flash red color three times to indicate failure
    color.red = 255;
  }
  
#ifdef DEBUG
  Serial.print(F(" Calibration duration was "));
  Serial.print(time);
  Serial.println(F(" msec (Arduino clock)"));
  Serial.print(F(" Compensation factor is "));
  Serial.println(factor);
  if (factor <= 0) {
    Serial.println(F(" Compensation factor was rejected"));
  }
#endif

  if (pLedStrip != 0) {
    for (int i = 0; i < 3; i++) {
      if (i > 0) {
        delay(100);
      }
      pLedStrip->setColor(color);
      delay(100);
      pLedStrip->off();
    }
  }
}

bool readCalibrationData(calibration_data_t* data) {
  eeprom_read_block(data, 0, sizeof(calibration_data_t));
  if (data->magicBytes != CALIBRATION_MAGIC_BYTES) {
    assumeUncalibratedState(data);
    return false;
  } else {
    return true;
  }
}

void resetCalibrationData() {
  calibration_data_t defaultCalibrationData;
  assumeUncalibratedState(&defaultCalibrationData);
  writeCalibrationData(&defaultCalibrationData);
}

void writeCalibrationData(calibration_data_t* data) {
  /* Yes, the parameter ordering is correct */
  data->magicBytes = CALIBRATION_MAGIC_BYTES;
  eeprom_update_block(data, 0, sizeof(calibration_data_t));
}
