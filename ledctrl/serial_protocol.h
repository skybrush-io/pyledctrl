/**
 * \file serial_protocol.h
 * Class for handling incoming messages on the serial port.
 */

#ifndef SERIAL_PROTOCOL_H
#define SERIAL_PROTOCOL_H

#include <Arduino.h>

/**
 * Internal state of the serial protocol parser.
 */
namespace SerialProtocolParserState {
  enum Enum {
    START,                 ///< Waiting for text or binary message indicator
    TEXT_COMMAND_CODE,     ///< Waiting for command code in text mode
    TEXT_ARGUMENTS,        ///< Waiting for command arguments in text mode
    BINARY_LENGTH_1,       ///< Waiting for first byte of message length in binary mode
    BINARY_LENGTH_2,       ///< Waiting for second byte of message length in binary mode
    BINARY_COMMAND_CODE,   ///< Waiting for command code in binary mode
    BINARY_DATA,           ///< Waiting for arguments in binary mode
    TRAP                   ///< Error state; waits for the next newline
  };
}

/**
 * Parses and handles incoming messages on the serial port.
 */
class SerialProtocolParser {
private:
  /**
   * The state of the parser.
   */
  SerialProtocolParserState::Enum m_state;

public:
  explicit SerialProtocolParser() : m_state(SerialProtocolParserState::START) {
    reset();
  }

  /**
   * Feeds a single byte into the parser.
   * 
   * \param  character  the incoming byte from the serial port that we have just read
   */
  void feed(int character);
  
  /**
   * Resets the parser to its initial state.
   */
  void reset();
};

#endif
