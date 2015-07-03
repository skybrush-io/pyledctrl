#include "led_strip.h"

void LEDStrip::initialize() const {
  // Set the pins to OUTPUT mode
  pinMode(m_redPin, OUTPUT);
  pinMode(m_greenPin, OUTPUT);
  pinMode(m_bluePin, OUTPUT);
  setGray(0);
}
