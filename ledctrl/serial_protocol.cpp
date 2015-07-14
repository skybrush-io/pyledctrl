#include "serial_protocol.h"

using namespace SerialProtocolParserState;

void SerialProtocolParser::feed(int character) {
  switch (m_state) {
    case START:
    break;
    
    case TEXT_COMMAND_CODE:
    break;
    
    case TEXT_ARGUMENTS:
    break;
    
    case BINARY_LENGTH_1:
    break;

    case BINARY_LENGTH_2:
    break;

    case BINARY_COMMAND_CODE:
    break;

    case BINARY_DATA:
    break;

    case TRAP:
    break;

    default:
    break;
  }
}

void SerialProtocolParser::reset() {
  m_state = START;
}

