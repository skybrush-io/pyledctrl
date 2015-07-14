/**
 * \file errors.h
 * Constants for handling errors during the execution of the bytecode.
 */

#ifndef ERRORS_H
#define ERRORS_H

#include "led.h"

namespace Errors {
  /**
   * Error codes emitted by the LED controller.
   */
  enum Code {
    SUCCESS,                           /**< No error */
    INVALID_COMMAND_CODE,              /**< Invalid command code found */
    SEEKING_NOT_SUPPORTED,             /**< Seeking not supported by the bytecode store */
    NUMBER_OF_ERRORS
  };
}

/**
 * \brief Error handler singleton.
 * 
 * This singleton may be accessed and used by other objects to signal an error
 * condition to the user via a LED.
 */
class ErrorHandler {
private:
  /**
   * Code of the last error that happened during execution.
   */
  Errors::Code m_error;

  /**
   * LED that is used to signal error conditions.
   */
  const LED* m_pLED;

public:
  /**
   * Returns the only instance of the error handler.
   */
  static ErrorHandler& instance() {
    static ErrorHandler myInstance;
    return myInstance;
  }

  /**
   * Tells the error handler that there is no error condition at the moment.
   */
  void clearError();
  
  /**
   * Asks the error handler to handle the given error condition.
   * 
   * \param  code  the code of the error
   */
  void error(Errors::Code code);

  /**
   * Attaches the given LED to the error handler.
   * 
   * \param  led  the LED that will be used to indicate error conditions
   */
  void setErrorLED(const LED* led);
  
private:
  /**
   * Constructor. This is intentionally private as we don't want the user to
   * instantiate this object.
   */
  ErrorHandler() : m_error(Errors::SUCCESS), m_pLED(0) {}

  /**
   * Copy constructor. Intentionally left unimplemented to prevent the user
   * from copying the singleton instance.
   */
  ErrorHandler(ErrorHandler const&);

  /**
   * Assignment operator. Intentionally left unimplemented to prevent the
   * user from copying the singleton instance.
   */
  void operator=(ErrorHandler const&);

  /**
   * Updates the status of the error LED after the error code or the assigned
   * LED has changed.
   */
  void updateLEDStatus() const;
};

/**
 * \def SET_ERROR
 * 
 * Shorthand notation for setting an error code in the global error handler.
 */
#define SET_ERROR(code) ErrorHandler::instance().error(code)

/**
 * \def CLEAR_ERROR
 * 
 * Shorthand notation for clearing the error condition in the global error handler.
 */
#define CLEAR_ERROR ErrorHandler::instance().clearError

#endif
