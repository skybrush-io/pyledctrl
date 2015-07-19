#include "errors.h"

void ErrorHandler::clearError() {
  error(Errors::SUCCESS);
}

void ErrorHandler::error(Errors::Code code) {
  if (code == m_error)
    return;
  
  if (m_error == Errors::SUCCESS) {
    // Moving from a non-error state to an error state,
    // so let's report the error code on the serial line.
    // Further error codes are suppressed to avoid flooding
    // the serial line.
    Serial.print("E");
    Serial.println(code, DEC);
  }
  
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
