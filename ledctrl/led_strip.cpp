#include "led_strip.h"

void LEDStrip::initialize() {
  // Set the pins to OUTPUT mode
  pinMode(m_redPin, OUTPUT);
  pinMode(m_greenPin, OUTPUT);
  pinMode(m_bluePin, OUTPUT);
  
  // Define voltage compensation ranges for the diodes
  CalculateRanges();
  // Turn off the LEDs
  off();
}
/*
LEDStrip::normalizeVoltage(float voltage) const {
  return static_cast<byte>(254 * voltage / BOARD_MAX_INPUT_VOLTAGE);
}*/
