#include "serial_protocol.h"

using namespace SerialProtocolParserState;
using namespace SerialProtocolCommand;

#define CMD_FLAG_NO_ARGS 1
#define CMD_FLAG_BINARY  2

bool SerialCommandInfo::needsBinaryMode() const {
  return flags & CMD_FLAG_BINARY;
}

bool SerialCommandInfo::hasArguments() const {
  return !(flags & CMD_FLAG_NO_ARGS);
}

const SerialCommandInfo SERIAL_COMMAND_INFO[] = {
  {
    /* .commandCode = */ REWIND,
    /* .flags = */ CMD_FLAG_NO_ARGS,
  },
  {
    /* .commandCode = */ RESUME,
    /* .flags = */ CMD_FLAG_NO_ARGS,
  },
  {
    /* .commandCode = */ SUSPEND,
    /* .flags = */ CMD_FLAG_NO_ARGS,
  },
  {
    /* .commandCode = */ TERMINATE,
    /* .flags = */ CMD_FLAG_NO_ARGS,
  },
  {
    /* .commandCode = */ UPLOAD,
    /* .flags = */ 0,
  },
  {
    /* .commandCode = */ UPLOAD_BIN,
    /* .flags = */ CMD_FLAG_BINARY,
  },
  {
    /* .commandCode = */ EXECUTE,
    /* .flags = */ 0,
  },
  {
    /* .commandCode = */ EXECUTE_BIN,
    /* .flags = */ CMD_FLAG_BINARY
  },
  
  /* sentinel element, this must always be the last one */
  {
    /* .commandCode = */ NO_COMMAND
  }
};

/**
 * \brief Returns the info entry for the command with the given code.
 * 
 * \param  code  the code of the command
 * \return the info entry of the command or \c NULL if there is no such command
 */
static const SerialCommandInfo* findInfoForCommandCode(SerialProtocolCommand::Code code) {
  const SerialCommandInfo* info = SERIAL_COMMAND_INFO;
  while (info->commandCode != NO_COMMAND) {
    if (info->commandCode == code) {
      return info;
    }
    info++;
  }
  return 0;
}

void SerialProtocolParser::executeCurrentCommand() {
  BytecodeStore* bytecodeStore;
  Errors::Code errorCode = Errors::SUCCESS;
  
  if (m_pCommandInfo == 0)
    return;
  
  assert(m_pCommandExecutor != 0);

  switch (m_pCommandInfo->commandCode) {
    case REWIND:
      m_pCommandExecutor->rewind();
      break;

    case RESUME:
    case SUSPEND:
      bytecodeStore = m_pCommandExecutor->bytecodeStore();
      if (!bytecodeStore) {
        errorCode = Errors::NO_BYTECODE_STORE;
      }
      if (m_pCommandInfo->commandCode == RESUME) {
        if (bytecodeStore->suspended()) {
          bytecodeStore->resume();
        } else {
          errorCode = Errors::OPERATION_NOT_SUPPORTED;
        }
      } else {
        bytecodeStore->suspend();
      }
      break;
      
    case TERMINATE:
      m_pCommandExecutor->stop();
      break;
      
    default:
      errorCode = Errors::OPERATION_NOT_IMPLEMENTED;
      return;
  }

  if (errorCode == Errors::SUCCESS) {
    Serial.println("+OK");
  } else {
    writeErrorCode(errorCode);
  }
}

void SerialProtocolParser::setCommandExecutor(CommandExecutor* executor) {
  m_pCommandExecutor = executor;
}
  
void SerialProtocolParser::writeErrorCode(Errors::Code code) const {
  Serial.print(F("-E"));
  Serial.println(code, DEC);
}

void SerialProtocolParser::feed(int character) {
  const SerialCommandInfo* commandInfo;

  /*
  Serial.print(" State = ");
  Serial.println(m_state);
  Serial.print(" Character = ");
  Serial.println(character, DEC);
  */
  
  if (character == -1) {
    // No character was read from the serial port
    return;
  }
  
  switch (m_state) {
    case START:
      reset();

      if (character == '\n' || character == '\r') {
        // Newline characters, just stay in the same state
      } else {
        commandInfo = findInfoForCommandCode(
          static_cast<SerialProtocolCommand::Code>(character & 0xFF)
        ); 
        if (commandInfo == 0) {
          // Invalid command code
          // Ignore everything up to the next newline
          m_state = TRAP;
        } else {
          m_pCommandInfo = commandInfo;
          if (!commandInfo->hasArguments()) {
            // Command has no arguments
            m_state = COMMAND_WITH_NO_ARGS;
          } else if (commandInfo->needsBinaryMode()) {
            // This will be a binary message
            m_state = BINARY_LENGTH_1;
          } else {
            // This will be a text message
            m_state = TEXT_ARGUMENTS;
          }
        }
      }
      break;
    
    case TEXT_ARGUMENTS:
      if (character == '\n' || character == '\r') {
        // Got a newline, so we can process this message and then start
        // parsing again.
        executeCurrentCommand();
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
      m_remainingMessageLength = m_nextMessageLength;
      m_state = (m_remainingMessageLength > 0) ? BINARY_DATA : START;
      break;

    case BINARY_DATA:
      // TODO
      m_remainingMessageLength--;
      if (m_remainingMessageLength == 0) {
        executeCurrentCommand();
        m_state = START;
      }
      break;

    case COMMAND_WITH_NO_ARGS:
      if (character == '\n' || character == '\r') {
        // Got a newline, execute the command and start parsing the next command
        executeCurrentCommand();
        m_state = START;
      } else {
        // Move to the trap state since we should have not received anything
        // but a newline
        m_state = TRAP;
      }
      break;
    
    case TRAP:
      if (character == '\n' || character == '\r') {
        // Got a newline, start parsing again, but indicate that
        // we had problems with understanding this command
        writeErrorCode(Errors::SERIAL_PROTOCOL_PARSE_ERROR);
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
  m_pCommandInfo = 0;
  m_nextMessageLength = 0;
  m_remainingMessageLength = 0;
}

