#include "errors.h"

void ErrorHandler::clearError() {
  error(Errors::SUCCESS);
}

void ErrorHandler::error(Errors::Code code) {
  m_error = code;
  updateLEDStatus();
}

void ErrorHandler::setErrorLED(const LED* led) {
  if (m_pLED) {
    m_pLED->off();
  }
  
  m_pLED = led;
  updateLEDStatus();
}

void ErrorHandler::updateLEDStatus() const {
  if (m_pLED) {
    if (m_error != Errors::SUCCESS) {
      m_pLED->on();
    } else {
      m_pLED->off();
    }
  }
}
