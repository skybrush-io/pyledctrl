#include "pyro.h"

void Pyro::initialize() {
  // Set the pin to OUTPUT mode
  pinMode(m_Pin, OUTPUT);
  // Turn off the pyro trigger at init but do not enable ON yet
  off(0);
}

void Pyro::off(u8 enableOn) {
  LED_PIN_WRITE(m_Pin, 0);
  m_LastSwitchOnTime = 0;
  if (enableOn) {
    m_EnableOn = 1;
  }
#ifdef DEBUG
  Serial.print(" Pyro OFF");
#endif
}

void Pyro::on() {
  if (m_EnableOn) {
    LED_PIN_WRITE(m_Pin, 255);
    m_LastSwitchOnTime = millis();
#ifdef DEBUG
    Serial.print(" Pyro ON");
#endif
  }
#ifdef DEBUG
  else { Serial.print(" Pyro ON not enabled"); }
#endif
}


void Pyro::step() {
  // turn pyro off after a given pulse length
  if (m_LastSwitchOnTime) {
    if (millis() - m_LastSwitchOnTime >= PYRO_PULSE_LENGTH_IN_SECONDS*1000) {
      off();
    }
  }
}