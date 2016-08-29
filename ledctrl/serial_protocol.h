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
    CAPACITY    = 'c',      ///< Prints the capacity of the bytecode store
    RESUME      = 'r',      ///< Resumes the execution of the bytecode
    SUSPEND     = 's',      ///< Suspends the execution of the bytecode
    TERMINATE   = 't',      ///< Terminates the execution of the bytecode
    UPLOAD      = 'u',      ///< Uploads a chunk of bytecode, overwriting the bytecode store (text version)
    UPLOAD_BIN  = 'U',      ///< Uploads a chunk of bytecode, overwriting the bytecode store (binary version)
    VERSION     = 'v',      ///< Prints the version number
    EXECUTE     = 'x',      ///< Executes some bytecode command immediately, overwriting the bytecode store (text version)
    EXECUTE_BIN = 'X',      ///< Executes some bytecode command immediately, overwriting the bytecode store (binary version)
    QUERY       = '?',      ///< Run a status query. Body is ignored; controller always responds with "+READY."
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
   * Returns whether the command ignores everything between the command character and the
   * end of the line.
   */
  bool ignoresArguments() const;
  
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
    START,                   ///< Waiting for command code
    TEXT_ARGUMENTS,          ///< Waiting for command arguments in text mode
    BINARY_LENGTH_1,         ///< Waiting for first byte of message length in binary mode
    BINARY_LENGTH_2,         ///< Waiting for second byte of message length in binary mode
    BINARY_DATA,             ///< Waiting for command arguments in binary mode
    COMMAND_WITH_NO_ARGS,    ///< Waiting for newline character at the end of a command with no args
    COMMAND_WITH_IGNORED_ARGS,  ///< Waiting for newline character at the end of a command with ignored args
    TRAP                     ///< Error state; waits for the next newline
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

  /**
   * Stores the value of the current command line argument being parsed in text mode.
   * -1 is a special value; it means that we have not received any character that 
   * corresponds to a command line argument yet.
   */
  int m_currentArgument;

  /**
   * Stores the value of an error code during the execution of a command.
   */
  Errors::Code m_currentErrorCode;
  
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
   * Appends the given hexadecimal digit to the value of the current command
   * argument being parsed.
   * 
   * \param  digit  the digit to append
   */
  void appendHexDigitToCurrentArgument(u8 digit);
  
  /**
   * Returns the bytecode store of the current command executor.
   * 
   * \return  the bytecode store or \c NULL if there is no bytecode store or
   *          no command executor.
   */
  BytecodeStore* bytecodeStore() const;
  
  /**
   * Hook function that is called when the execution of the currently parsed command 
   * should finish. This happens after the terminating newline characters have been
   * received and parsed.
   */
  void finishExecutionOfCurrentCommand();

  /**
   * Handles a single argument byte of the current command. This hook function is called
   * every time a new byte is received and parsed for the current command.
   * 
   * \param  value  the value of the argument
   */
  void handleCommandArgument(u8 value);
  
  /**
   * Hook function that is called when the execution of the currently parsed command 
   * is about to start. This happens right after having received the command code. 
   */
  void startExecutionOfCurrentCommand();

  /**
   * Prints the given error code to the serial console.
   * 
   * \param  code  the code to print
   */
  void writeErrorCode(Errors::Code code) const;
};

#endif
