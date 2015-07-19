/**
 * \file serial_protocol.h
 * Class for handling incoming messages on the serial port.
 */

#ifndef SERIAL_PROTOCOL_H
#define SERIAL_PROTOCOL_H

#include <Arduino.h>
#include "errors.h"
#include "executor.h"

/**
 * Constants that denote the various commands that one can use in the
 * serial protocol.
 */
namespace SerialProtocolCommand {
  enum Code {
    NO_COMMAND  = 0,        ///< No command
    REWIND      = '<',      ///< Rewinds the execution to the start of the bytecode store
    RESUME      = 'r',      ///< Resumes the execution of the bytecode
    SUSPEND     = 's',      ///< Suspends the execution of the bytecode
    TERMINATE   = 't',      ///< Terminates the execution of the bytecode
    UPLOAD      = 'u',      ///< Uploads a chunk of bytecode, overwriting the bytecode store (text version)
    UPLOAD_BIN  = 'U',      ///< Uploads a chunk of bytecode, overwriting the bytecode store (binary version)
    EXECUTE     = 'x',      ///< Executes some bytecode command immediately, overwriting the bytecode store (text version)
    EXECUTE_BIN = 'X',      ///< Executes some bytecode command immediately, overwriting the bytecode store (binary version)
  };
}

/**
 * Flag bits that are used in the 'flags' member of \c SerialCommandInfo.
 */
 
/**
 * Structure that defines the extra information we provide about each
 * command of the serial protocol such as whether the command arguments
 * are to be provided in binary or text mode.
 */
typedef struct {
public:
  /**
   * The character code of the command.
   */
  SerialProtocolCommand::Code commandCode;

  /**
   * The info flags of the command that define whether the command has arguments and
   * if so, whether these arguments are expected in text or binary form.
   */
  u8 flags;
  
  /**
   * Returns whether the command has at least one argument.
   */
  bool hasArguments() const;
  
  /**
   * Returns whether the command expects its arguments in text or binary mode.
   */
  bool needsBinaryMode() const;

} SerialCommandInfo;

/**
 * Array that holds information for each of the commands on the serial port that we support.
 */
extern const SerialCommandInfo SERIAL_COMMAND_INFO[];

/**
 * Internal state of the serial protocol parser.
 */
namespace SerialProtocolParserState {
  enum Enum {
    START,                 ///< Waiting for command code
    TEXT_ARGUMENTS,        ///< Waiting for command arguments in text mode
    BINARY_LENGTH_1,       ///< Waiting for first byte of message length in binary mode
    BINARY_LENGTH_2,       ///< Waiting for second byte of message length in binary mode
    BINARY_DATA,           ///< Waiting for command arguments in binary mode
    COMMAND_WITH_NO_ARGS,  ///< Waiting for newline character at the end of a command with no args
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

  /**
   * Information about the current command being parsed.
   */
  const SerialCommandInfo* m_pCommandInfo;
  
  /**
   * The length of the binary message being parsed. 
   */
  uint16_t m_nextMessageLength;
  
  /**
   * The remaining length of the next binary message expected by the parser.
   */
  uint16_t m_remainingMessageLength;

  /**
   * Pointer to the bytecode executor that the parser will manipulate.
   */
  CommandExecutor* m_pCommandExecutor;
  
public:
  explicit SerialProtocolParser() : m_pCommandExecutor(0) {
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

  /**
   * Sets the command executor that the parser will manipulate in response to some
   * of the commands.
   */
  void setCommandExecutor(CommandExecutor* executor);
  
private:
  /**
   * Executes the currently parsed command.
   */
  void executeCurrentCommand();
  
  /**
   * Prints the given error code to the serial console.
   * 
   * \param  code  the code to print
   */
  void writeErrorCode(Errors::Code code) const;
};

#endif
