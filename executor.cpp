#include <assert.h>
#include "commands.h"
#include "config.h"
#include "executor.h"
#include "led.h"
#include "led_strip.h"

void CommandExecutor::delayExecutionFor(unsigned long duration) {
  delayExecutionUntil(m_currentCommandStartTime + duration);
}

void CommandExecutor::delayExecutionUntil(unsigned long ms) {
  m_nextWakeupTime = ms;
}

void CommandExecutor::error(command_executor_error_t code) {
  m_error = code;
  if (m_pErrorLED) {
    if (m_error != ERR_SUCCESS) {
      m_pErrorLED->on();
    } else {
      m_pErrorLED->off();
    }
  }
}

void CommandExecutor::executeNextCommand() {
  u8 commandCode;
  
  if (m_ended) {
    return;
  }

  commandCode = nextByte();
#ifdef DEBUG
  Serial.print("[");
  Serial.print(clock());
  Serial.print(" ms] Command: ");
  Serial.println(commandCode);
#endif

  switch (commandCode) {
    case CMD_END:             /* End of program */
      stop();
      break;

    case CMD_NOP:             /* Do nothing */
      break;

    case CMD_SET_COLOR:       /* Set the color of the LED strip and wait */
      handleSetColorCommand();
      break;
      
    case CMD_SET_GRAY:        /* Set the color of the LED strip to a shade of gray and wait */
      handleSetGrayCommand();
      break;
      
    case CMD_SET_BLACK:       /* Set the color of the LED strip to black and wait */
      handleSetBlackCommand();
      break;
      
    case CMD_SET_WHITE:       /* Set the color of the LED strip to white and wait */
      handleSetWhiteCommand();
      break;

    case CMD_SLEEP:           /* Sleeps for a given duration */
      handleSleepCommand();
      break;

    case CMD_WAIT_UNTIL:      /* Waits until the internal clock of the executor reaches a given value */
      handleWaitUntilCommand();
      break;
      
    case CMD_LOOP_BEGIN:      /* Marks the beginning of a loop */
      handleLoopBeginCommand();
      break;
      
    case CMD_LOOP_END:        /* Marks the end of a loop */
      handleLoopEndCommand();
      break;
      
    default:
      /* Unknown command code, stop execution and set an error condition */
      error(ERR_INVALID_COMMAND_CODE);
      stop();
  }
}

void CommandExecutor::handleDelayByte() {
  u8 encodedDuration;
  unsigned long duration;
  
  encodedDuration = nextByte();

  /* If the two most significant bits are 1, the remaining six bits
   * denote units of 1/32-th of a second.
   */
  if ((encodedDuration & 0xC0) == 0xC0) {
    /* 1/32 sec = 31.25 msec
     * x*31.25 = x*31 + (x >> 2)
     * x*31 + (x >> 2) = (x << 5) - x + (x >> 2)
     */
    encodedDuration &= 0x3F;
    duration = encodedDuration & 0x3F;
    duration = (duration << 5) - duration + (duration >> 2);
  } else {
    /* The value denotes whole seconds */
    duration = encodedDuration * 1000;
  }

#ifdef DEBUG
  Serial.print("Delay: ");
  Serial.print(duration);
  Serial.println(" msec");
#endif

  delayExecutionFor(duration);
}

void CommandExecutor::load(const u8* bytecode) {
  m_bytecode = bytecode;
  rewind();
}

u8 CommandExecutor::nextByte() {
  assert(m_pNextCommand != 0);
  return *(m_pNextCommand++);
}

unsigned long CommandExecutor::nextVarint() {
  unsigned long result = 0;
  u8 readByte;
  u8 shift = 0;

  do {
    readByte = nextByte();
    result |= ((unsigned long)(readByte & 0x7F)) << shift;
    shift += 7;
  } while (readByte & 0x80);

  return result;
}

void CommandExecutor::rewind() {
  m_pNextCommand = m_bytecode;
  m_ended = (m_bytecode == 0);
  m_loopStack.clear();
  error(ERR_SUCCESS);
  delayExecutionFor(0);
}

unsigned long CommandExecutor::step() {
  unsigned long now = millis();
  if (now >= m_nextWakeupTime) {
    m_currentCommandStartTime = now;
    executeNextCommand();
  }
  return m_nextWakeupTime;
}

void CommandExecutor::stop() {
  m_ended = true;
}

/********************/
/* Command handlers */
/********************/

void CommandExecutor::handleLoopBeginCommand() {
  u8 iterations = nextByte();

#ifdef DEBUG
  Serial.print("Starting loop #");
  Serial.print(m_loopStack.size());
  Serial.print(" with ");
  Serial.print(iterations);
  Serial.println(" iteration(s)");
#endif

  m_loopStack.begin(m_pNextCommand, iterations);
}

void CommandExecutor::handleLoopEndCommand() {
  const u8* jumpTo = m_loopStack.end();
  
#ifdef DEBUG
  if (jumpTo == 0) {
    Serial.print("Loop #");
    Serial.print(m_loopStack.size());
    Serial.println(" terminated");
  } else {
    Serial.print("Restarting loop #");
    Serial.println(m_loopStack.size());
  }
#endif

  if (jumpTo != 0) {
    m_pNextCommand = jumpTo;
  }
}

void CommandExecutor::handleResetClockCommand() {
  m_lastClockResetTime = m_currentCommandStartTime;
}

void CommandExecutor::handleSetBlackCommand() {
  assert(m_pLEDStrip != 0);
  m_pLEDStrip->off();
  handleDelayByte();
}

void CommandExecutor::handleSetColorCommand() {
  u8 red = nextByte();
  u8 green = nextByte();
  u8 blue = nextByte();
  
#ifdef DEBUG
  Serial.print("Arguments: ");
  Serial.print(red);
  Serial.print(' ');
  Serial.print(green);
  Serial.print(' ');
  Serial.println(blue);
#endif

  assert(m_pLEDStrip != 0);
  m_pLEDStrip->setColor(red, green, blue);
  handleDelayByte();
}

void CommandExecutor::handleSetGrayCommand() {
  u8 gray = nextByte();
  
#ifdef DEBUG
  Serial.print("Arguments: ");
  Serial.println(gray);
#endif

  assert(m_pLEDStrip != 0);
  m_pLEDStrip->setGray(gray);
  handleDelayByte();
}

void CommandExecutor::handleSetWhiteCommand() {
  assert(m_pLEDStrip != 0);
  m_pLEDStrip->on();
  handleDelayByte();
}

void CommandExecutor::handleSleepCommand() {
  handleDelayByte();
}

void CommandExecutor::handleWaitUntilCommand() {
  unsigned long deadline = nextVarint();
  
#ifdef DEBUG
  Serial.print("Arguments: ");
  Serial.println(deadline);
#endif

  delayExecutionUntil(m_lastClockResetTime + deadline);
}
