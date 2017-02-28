#include "pyro.h"

void Pyro::initialize() {
  // Set the pin to OUTPUT mode
  pinMode(m_Pin, OUTPUT);
  // Turn off the pyro trigger
  off();
}
