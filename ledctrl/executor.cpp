#include <assert.h>
#include "bytecode_store.h"
#include "colors.h"
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
  Serial.print(F(" ["));
  Serial.print(clock());
  Serial.print(F(" ms] Command: "));
  Serial.println(commandCode);
#endif

  switch (commandCode) {
    case CMD_END:             /* End of program */
      stop();
      break;

    case CMD_NOP:             /* Do nothing */
      break;

    case CMD_SLEEP:           /* Sleeps for a given duration */
      handleSleepCommand();
      break;

    case CMD_WAIT_UNTIL:      /* Waits until the internal clock of the executor reaches a given value */
      handleWaitUntilCommand();
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

    case CMD_FADE_TO_COLOR:   /* Fades the color of the LED strip */
      handleFadeToColorCommand();
      break;
      
    case CMD_FADE_TO_GRAY:    /* Fades the color of the LED strip to a shade of gray */
      handleFadeToGrayCommand();
      break;
      
    case CMD_FADE_TO_BLACK:   /* Fades the color of the LED strip to black */
      handleFadeToBlackCommand();
      break;
      
    case CMD_FADE_TO_WHITE:   /* Fades the color of the LED strip to white */
      handleFadeToWhiteCommand();
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

void CommandExecutor::fadeColorOfLEDStrip(rgb_color_t color) {
  unsigned long duration = handleDelayByte();
  EasingMode easingMode = handleEasingModeByte();
  
  m_ledStripFader.endColor = color;
  m_transition.setEasingMode(easingMode);
  m_transition.start(duration, m_currentCommandStartTime);
  m_transition.step(m_ledStripFader);
}

unsigned long CommandExecutor::handleDelayByte() {
  unsigned long duration = nextDuration();
  
#ifdef DEBUG
  Serial.print(F(" Delay: "));
  Serial.print(duration);
  Serial.println(F(" msec"));
#endif

  delayExecutionFor(duration);
  return duration;
}

EasingMode CommandExecutor::handleEasingModeByte() {
  u8 easingModeByte = nextByte();
  
#ifdef DEBUG
  Serial.print(F(" Easing mode: "));
  Serial.println(easingModeByte);
#endif

  return static_cast<EasingMode>(easingModeByte);
}

u8 CommandExecutor::nextByte() {
  assert(m_pBytecodeStore != 0);
  return m_pBytecodeStore->next();
}

unsigned long CommandExecutor::nextDuration() {
  u8 encodedDuration = nextByte();
  unsigned long duration;
  
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

  return duration;
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
  if (m_pBytecodeStore) {
    m_pBytecodeStore->rewind();
    m_ended = m_pBytecodeStore->empty();
  } else {
    m_ended = true;
  }
  m_loopStack.clear();
  error(ERR_SUCCESS);
  delayExecutionFor(0);
}

void CommandExecutor::setColorOfLEDStrip(rgb_color_t color) {
  handleDelayByte();
  
  assert(m_pLEDStrip != 0);
  m_pLEDStrip->setColor(color);
  m_ledStripFader.startColor = color;
}

unsigned long CommandExecutor::step() {
  unsigned long now = millis();
  
  if (m_transition.active()) {
    if (!m_transition.step(m_ledStripFader, now)) {
      // Transition not active any more; make sure that the next
      // transition starts from the current end color
      m_ledStripFader.startColor = m_ledStripFader.endColor;
    }
  }
  
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

void CommandExecutor::handleFadeToBlackCommand() {
  fadeColorOfLEDStrip(COLOR_BLACK);
}

void CommandExecutor::handleFadeToColorCommand() {
  rgb_color_t color;
  
  color.red = nextByte();
  color.green = nextByte();
  color.blue = nextByte();
  
#ifdef DEBUG
  Serial.print(F(" Arguments: "));
  Serial.print(color.red);
  Serial.print(' ');
  Serial.print(color.green);
  Serial.print(' ');
  Serial.println(color.blue);
#endif

  fadeColorOfLEDStrip(color);
}

void CommandExecutor::handleFadeToGrayCommand() {
  rgb_color_t color;
  
  color.red = color.green = color.blue = nextByte();
  
#ifdef DEBUG
  Serial.print(F(" Arguments: "));
  Serial.println(color.red);
#endif

  fadeColorOfLEDStrip(color);
}

void CommandExecutor::handleFadeToWhiteCommand() {
  fadeColorOfLEDStrip(COLOR_WHITE);
}

void CommandExecutor::handleLoopBeginCommand() {
  u8 iterations = nextByte();
  bytecode_location_t location = m_pBytecodeStore->tell();

  if (location == BYTECODE_LOCATION_NOWHERE) {
    error(ERR_SEEKING_NOT_SUPPORTED);
    stop();
    return;
  }
  
#ifdef DEBUG
  Serial.print(F(" Starting loop #"));
  Serial.print(m_loopStack.size());
  Serial.print(F(" with "));
  Serial.print(iterations);
  Serial.println(F(" iteration(s)"));
#endif

  m_loopStack.begin(location, iterations);
}

void CommandExecutor::handleLoopEndCommand() {
  bytecode_location_t jumpTo = m_loopStack.end();
  
#ifdef DEBUG
  if (jumpTo == BYTECODE_LOCATION_NOWHERE) {
    Serial.print(F(" Loop #"));
    Serial.print(m_loopStack.size());
    Serial.println(F(" terminated"));
  } else {
    Serial.print(F(" Restarting loop #"));
    Serial.println(m_loopStack.size());
  }
#endif

  if (jumpTo != BYTECODE_LOCATION_NOWHERE) {
    m_pBytecodeStore->seek(jumpTo);
  }
}

void CommandExecutor::handleResetClockCommand() {
  m_lastClockResetTime = m_currentCommandStartTime;
}

void CommandExecutor::handleSetBlackCommand() {
  setColorOfLEDStrip(COLOR_BLACK);
}

void CommandExecutor::handleSetColorCommand() {
  rgb_color_t color;
  
  color.red = nextByte();
  color.green = nextByte();
  color.blue = nextByte();
  
#ifdef DEBUG
  Serial.print(F(" Arguments: "));
  Serial.print(color.red);
  Serial.print(' ');
  Serial.print(color.green);
  Serial.print(' ');
  Serial.println(color.blue);
#endif

  setColorOfLEDStrip(color);
}

void CommandExecutor::handleSetGrayCommand() {
  rgb_color_t color;
  
  color.red = color.green = color.blue = nextByte();
  
#ifdef DEBUG
  Serial.print(F(" Arguments: "));
  Serial.println(color.red);
#endif

  setColorOfLEDStrip(color);
}

void CommandExecutor::handleSetWhiteCommand() {
  setColorOfLEDStrip(COLOR_WHITE);
}

void CommandExecutor::handleSleepCommand() {
  handleDelayByte();
}

void CommandExecutor::handleWaitUntilCommand() {
  unsigned long deadline = nextVarint();
  
#ifdef DEBUG
  Serial.print(F(" Arguments: "));
  Serial.println(deadline);
#endif

  delayExecutionUntil(m_lastClockResetTime + deadline);
}
