#include "commands.h"
#include "serial_protocol.h"
#include "version.h"

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
    /* .commandCode = */ CAPACITY,
    /* .flags = */ CMD_FLAG_NO_ARGS,
  },
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
    /* .commandCode = */ VERSION,
    /* .flags = */ CMD_FLAG_NO_ARGS,
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
 * \def Macro that defines the separator characters between arguments in text mode.
 */
#define IS_TEXT_ARGUMENT_SEPARATOR(ch) ((ch) == ' ' || (ch) == '\t' || (ch) == ',' || (ch) == ';')

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

BytecodeStore* SerialProtocolParser::bytecodeStore() const {
  return m_pCommandExecutor ? m_pCommandExecutor->bytecodeStore() : 0;
}

void SerialProtocolParser::startExecutionOfCurrentCommand() {
  BytecodeStore* bytecodeStore;
  
  if (m_pCommandInfo == 0)
    return;
  
  assert(m_pCommandExecutor != 0);

  m_currentErrorCode = Errors::SUCCESS;
  
  switch (m_pCommandInfo->commandCode) {
    case EXECUTE:
    case EXECUTE_BIN:
    case UPLOAD:
    case UPLOAD_BIN:
      bytecodeStore = this->bytecodeStore();
      if (bytecodeStore == 0) {
        m_currentErrorCode = Errors::NO_BYTECODE_STORE;
      } else {
        m_pCommandExecutor->rewind();
        bytecodeStore->suspend();
      }
      break;
  }
}

void SerialProtocolParser::finishExecutionOfCurrentCommand() {
  BytecodeStore* bytecodeStore;
  bool suppressOk = 0;
  
  if (m_pCommandInfo == 0)
    return;
  
  assert(m_pCommandExecutor != 0);

  switch (m_pCommandInfo->commandCode) {
    case REWIND:
      m_pCommandExecutor->rewind();
      break;

    case TERMINATE:
      m_pCommandExecutor->stop();
      break;
      
    case RESUME:
    case SUSPEND:
      bytecodeStore = this->bytecodeStore();
      if (!bytecodeStore) {
        m_currentErrorCode = Errors::NO_BYTECODE_STORE;
      } else {
        if (m_pCommandInfo->commandCode == RESUME) {
          if (bytecodeStore->suspended()) {
            bytecodeStore->resume();
          } else {
            m_currentErrorCode = Errors::OPERATION_NOT_SUPPORTED;
          }
        } else {
          bytecodeStore->suspend();
        }
      }
      break;

    case CAPACITY:
      bytecodeStore = this->bytecodeStore();
      if (!bytecodeStore) {
        m_currentErrorCode = Errors::NO_BYTECODE_STORE;
      } else {
        Serial.print("+");
        Serial.println(bytecodeStore->capacity(), DEC);
        suppressOk = true;
      }
      break;
      
    case VERSION:
      Serial.print("+");
      Serial.print(LEDCTRL_VERSION_MAJOR, DEC);
      Serial.print(".");
      Serial.print(LEDCTRL_VERSION_MINOR, DEC);
      Serial.print(".");
      Serial.println(LEDCTRL_VERSION_PATCH, DEC);
      suppressOk = true;
      break;
    
    case EXECUTE:
    case EXECUTE_BIN:
    case UPLOAD:
    case UPLOAD_BIN:
      bytecodeStore = this->bytecodeStore();
      if (!bytecodeStore) {
        m_currentErrorCode = Errors::NO_BYTECODE_STORE;
      } else {
        // Add a terminating CMD_END if needed to ensure that we do not accidentally read parts of the
        // memory that we are not supposed to
        if (m_pCommandInfo->commandCode == EXECUTE || m_pCommandInfo->commandCode == EXECUTE_BIN) {
          // TODO: syntax checking for the uploaded command to see if we have all the args?
          if (bytecodeStore->write(CMD_END) == 0) {
            m_currentErrorCode = Errors::OPERATION_NOT_SUPPORTED;
          }
        }
        // Rewind the command executor and resume execution
        m_pCommandExecutor->rewind();
        bytecodeStore->resume();
      }
      break;
      
    default:
      m_currentErrorCode = Errors::OPERATION_NOT_IMPLEMENTED;
      return;
  }

  if (m_currentErrorCode == Errors::SUCCESS) {
    if (!suppressOk) {
      Serial.println(F("+OK"));
    }
  } else {
    writeErrorCode(m_currentErrorCode);
  }
}

void SerialProtocolParser::handleCommandArgument(u8 value) {
  BytecodeStore* bytecodeStore;
  
  if (m_pCommandInfo == 0)
    return;
  
  assert(m_pCommandExecutor != 0);
  
  switch (m_pCommandInfo->commandCode) {
    case EXECUTE:
    case EXECUTE_BIN:
    case UPLOAD:
    case UPLOAD_BIN:
      bytecodeStore = this->bytecodeStore();
      if (bytecodeStore == 0) {
        m_currentErrorCode = Errors::NO_BYTECODE_STORE;
      } else {
        if (bytecodeStore->write(value) == 0) {
          m_currentErrorCode = Errors::OPERATION_NOT_SUPPORTED;
        }
      }
      break;
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
            m_currentArgument = -1;
            m_state = TEXT_ARGUMENTS;
          }
          startExecutionOfCurrentCommand();
        }
      }
      break;
    
    case TEXT_ARGUMENTS:
      if (character == '\n' || character == '\r') {
        // Got a newline, so we can process this message and then start
        // parsing again.
        if (m_currentArgument >= 0) {
          handleCommandArgument(m_currentArgument);
          m_currentArgument = -1;
        }
        finishExecutionOfCurrentCommand();
        m_state = START;
      } else if (IS_TEXT_ARGUMENT_SEPARATOR(character)) {
        // Separator character between arguments
        if (m_currentArgument >= 0) {
          handleCommandArgument(m_currentArgument);
          m_currentArgument = -1;
        }
      } else if (isdigit(character)) {
        appendHexDigitToCurrentArgument(character - '0');
      } else {
        character = toupper(character);
        if (character >= 'A' && character <= 'F') {
          // Hexadecimal digit
          appendHexDigitToCurrentArgument(character - 'A' + 10);
        } else {
          // Not a hexadecimal digit; the entire line is malformed
          m_state = TRAP;
        }
      }
      break;
    
    case BINARY_LENGTH_1:
      m_nextMessageLength = character;
      m_state = BINARY_LENGTH_2;
      break;

    case BINARY_LENGTH_2:
      m_nextMessageLength = m_nextMessageLength * 256 + character;
      m_remainingMessageLength = m_nextMessageLength;
      m_state = (m_remainingMessageLength > 0) ? BINARY_DATA : START;
      break;

    case BINARY_DATA:
      handleCommandArgument(static_cast<u8>(character));
      m_remainingMessageLength--;
      if (m_remainingMessageLength == 0) {
        finishExecutionOfCurrentCommand();
        m_state = START;
      } else if ((m_remainingMessageLength & 0x3F) == 0) {
        // After every 64 byte, print the number of bytes written into the bytecode
        // store as progress information
        Serial.print(':');
        Serial.println(m_nextMessageLength - m_remainingMessageLength);
      }
      break;

    case COMMAND_WITH_NO_ARGS:
      if (character == '\n' || character == '\r') {
        // Got a newline, execute the command and start parsing the next command
        finishExecutionOfCurrentCommand();
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

void SerialProtocolParser::appendHexDigitToCurrentArgument(u8 digit) {
  assert(digit >= 0 && digit < 16);
  if (m_currentArgument == -1) {
    m_currentArgument = 0;
  }
  m_currentArgument = (m_currentArgument << 4) + digit;
}

void SerialProtocolParser::reset() {
  m_state = START;
  m_pCommandInfo = 0;
  m_nextMessageLength = 0;
  m_remainingMessageLength = 0;
  m_currentArgument = -1;
  m_currentErrorCode = Errors::SUCCESS;
}

