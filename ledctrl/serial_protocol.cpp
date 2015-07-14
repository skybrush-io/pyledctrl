#include "errors.h"
#include "serial_protocol.h"

using namespace SerialProtocolParserState;

void SerialProtocolParser::feed(int character) {
  if (character == -1) {
    // No character was read from the serial port
    return;
  }
  
  switch (m_state) {
    case START:
      reset();
      if (character == 't') {
        // This will be a text message
        m_state = TEXT_COMMAND_CODE;
      } else if (character == 'b') {
        // This will be a binary message
        m_state = BINARY_LENGTH_1;
      } else if (character == '\n' || character == '\r') {
        // Newline characters, just stay in the same state
      } else {
        // Ignore everything up to the next newline
        m_state = TRAP;
      }
      break;
    
    case TEXT_COMMAND_CODE:
      m_commandCode = static_cast<u8>(character & 0xFF);
      m_state = TEXT_ARGUMENTS;
      break;
    
    case TEXT_ARGUMENTS:
      if (character == '\n' || character == '\r') {
        // Got a newline, so we can process this message and then start
        // parsing again.
        // TODO
        m_state = START;
      } else {
        // TODO
      }
      break;
    
    case BINARY_LENGTH_1:
      m_nextMessageLength = character & 0xFF;
      m_state = BINARY_LENGTH_2;
      break;

    case BINARY_LENGTH_2:
      m_nextMessageLength <<= 8;
      m_nextMessageLength += character & 0xFF;
      m_state = BINARY_COMMAND_CODE;
      break;

    case BINARY_COMMAND_CODE:
      m_commandCode = static_cast<u8>(character & 0xFF);
      m_remainingMessageLength = m_nextMessageLength;
      m_state = (m_remainingMessageLength > 0) ? BINARY_DATA : START;
      break;

    case BINARY_DATA:
      // TODO
      m_remainingMessageLength--;
      if (m_remainingMessageLength == 0) {
        m_state = START;
      }
      break;

    case TRAP:
      if (character == '\n' || character == '\r') {
        // Got a newline, start parsing again
        m_state = START;
      } else {
        // Otherwise stay in the trap state
      }
      break;

    default:
      SET_ERROR(Errors::SERIAL_PROTOCOL_INVALID_STATE);
      break;
  }
}

void SerialProtocolParser::reset() {
  m_state = START;
  m_commandCode = 0;
  m_nextMessageLength = 0;
  m_remainingMessageLength = 0;
}

