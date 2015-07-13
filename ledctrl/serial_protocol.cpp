#include "serial_protocol.h"

using namespace SerialProtocolParserState;

void SerialProtocolParser::feed(int character) {
  // TODO
}

void SerialProtocolParser::reset() {
  m_state = START;
}

