#include <assert.h>
#include <limits.h>
#include "bytecode_store.h"
#include "colors.h"
#include "commands.h"
#include "config.h"
#include "executor.h"
#include "led.h"
#include "led_strip.h"
#include "signal_decoders.h"

CommandExecutor::CommandExecutor(LEDStrip* pLEDStrip) : m_pLEDStrip(pLEDStrip),
      m_pBytecodeStore(0), m_ended(true), m_ledStripFader(pLEDStrip),
      m_clockSkewCompensationFactor(1)
{
  rewind();
};

signed long CommandExecutor::absoluteToInternalTime(unsigned long ms) {
  signed long msSigned = ms;
  return round((msSigned - m_lastClockResetTime) / m_clockSkewCompensationFactor);
}

void CommandExecutor::checkAndFireTriggers() {
  int i, n = MAX_TRIGGER_COUNT;
  bool fired;
  for (i = 0; i < n; i++) {
    fired = m_triggers[i].checkAndFireWhenNeeded();
    if (fired) {
      executeActionOfTrigger(&m_triggers[i]);
    }
  }
}

void CommandExecutor::delayExecutionFor(unsigned long duration) {
  delayExecutionUntilAbsoluteTime(millis() + duration * m_clockSkewCompensationFactor);
}

void CommandExecutor::delayExecutionUntil(unsigned long ms) {
#ifdef DEBUG
  signed long actualCompensatedDelay = internalToAbsoluteTime(ms) - m_lastClockResetTime;
  Serial.print(F(" Waiting until: "));
  Serial.print(ms);
  Serial.print(F(" msec (internal), "));
  Serial.print(actualCompensatedDelay);
  Serial.println(F(" msec (absolute)"));
#endif

  delayExecutionUntilAbsoluteTime(internalToAbsoluteTime(ms));
}

void CommandExecutor::delayExecutionUntilAbsoluteTime(unsigned long ms) {
  m_nextWakeupTime = ms;
}

void CommandExecutor::executeActionOfTrigger(const Trigger* trigger) {
  assert(trigger != 0);

  TriggerAction action = trigger->action();

  switch (action.type) {
    case TriggerActionType::RESUME:
      m_pBytecodeStore->resume();
      break;

    case TriggerActionType::JUMP_TO_ADDRESS:
      Serial.print(" Triggered jump to address ");
      Serial.println(action.arguments.address);
      m_pBytecodeStore->seek(action.arguments.address);
      break;

    default:
      SET_ERROR(Errors::INVALID_TRIGGER_ACTION_TYPE);
  }
}

void CommandExecutor::executeNextCommand() {
  u8 commandCode;

  if (m_ended) {
    return;
  }

  commandCode = nextByte();
#ifdef DEBUG
  if (m_pBytecodeStore && !m_pBytecodeStore->suspended()) {
    Serial.print(F(" [now="));
    Serial.print(absoluteToInternalTime(m_currentCommandStartTime));
    Serial.print(F(" ms, cum="));
    Serial.print(m_cumulativeDurationSinceStart);
    Serial.print(F(" ms] Command: "));
    Serial.println(commandCode);
  }
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

    case CMD_JUMP:            /* Unconditional jump to address */
      handleJumpCommand();
      break;

    case CMD_SET_COLOR_FROM_CHANNELS:        /* Set color from the current values of some channels */
      handleSetColorFromChannelsCommand();
      break;

    case CMD_FADE_TO_COLOR_FROM_CHANNELS:    /* Fade to color from the current values of some channels */
      handleFadeToColorFromChannelsCommand();
      break;

    default:
      /* Unknown command code, stop execution and set an error condition */
      SET_ERROR(Errors::INVALID_COMMAND_CODE);
      stop();
  }
}

void CommandExecutor::fadeColorOfLEDStrip(rgb_color_t color) {
  EasingMode easingMode = EASING_LINEAR;
  unsigned long desiredDuration = handleDelayByte();             // this is according to the internal clock
  unsigned long actualDuration = m_nextWakeupTime - millis();    // this is according to the Arduino's clock

  m_ledStripFader.endColor = color;
  m_transition.setEasingMode(easingMode);
  m_transition.start(actualDuration, m_currentCommandStartTime);
  m_transition.step(m_ledStripFader);
#ifdef DEBUG
  Serial.print(F(" Started transition with compensated duration = "));
  Serial.println(actualDuration);
#endif
}

Trigger* CommandExecutor::findTriggerForChannelIndex(u8 channelIndex) {
  u8 index;
  u8 freeTriggerIndex = 255;

  for (index = 0; index < MAX_TRIGGER_COUNT; index++) {
    if (m_triggers[index].channelIndex() == channelIndex) {
      return &m_triggers[index];
    } else if (freeTriggerIndex == 255 && !m_triggers[index].active()) {
      freeTriggerIndex = index;
    }
  }

  return freeTriggerIndex < 255 ? &m_triggers[freeTriggerIndex] : 0;
}

unsigned long CommandExecutor::handleDelayByte() {
  unsigned long duration = nextDuration();

#ifdef DEBUG
  Serial.print(F(" Delay: "));
  Serial.print(duration);
  Serial.println(F(" msec"));
#endif

  m_cumulativeDurationSinceStart += duration;             // this is according to the internal clock
  delayExecutionUntil(m_cumulativeDurationSinceStart);
  
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

unsigned long CommandExecutor::internalToAbsoluteTime(long ms) {
  return round(m_lastClockResetTime + ms * m_clockSkewCompensationFactor);
}

u8 CommandExecutor::nextByte() {
  assert(m_pBytecodeStore != 0);
  return m_pBytecodeStore->next();
}

unsigned long CommandExecutor::nextDuration() {
  unsigned long durationInHalfFrames = nextVarint();
  return durationInHalfFrames * 20;
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
  m_transition.cancel();
  
  CLEAR_ERROR();
  resetClock();
  delayExecutionFor(0);
}

void CommandExecutor::setColorOfLEDStrip(rgb_color_t color) {
  assert(m_pLEDStrip != 0);
  m_pLEDStrip->setColor(color);
  m_ledStripFader.startColor = color;
}

unsigned long CommandExecutor::step() {
  unsigned long now = millis();
  
  if (m_ended) {
    return now;
  }
  
  // Check the state of the signals being watched in the triggers
  checkAndFireTriggers();

  // Handle the active transition
  if (m_transition.active()) {
    if (!m_transition.step(m_ledStripFader, now)) {
      // Transition not active any more; make sure that the next
      // transition starts from the current end color
      m_ledStripFader.startColor = m_ledStripFader.endColor;
    }
  }

  // If the time has come, execute the next command
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

void CommandExecutor::handleFadeToColorFromChannelsCommand() {
  rgb_color_t color;
  u8 numChannels;
  u8 channelIndices[3];

  channelIndices[0] = nextByte();
  channelIndices[1] = nextByte();
  channelIndices[2] = nextByte();

#ifdef DEBUG
  Serial.print(F(" Arguments: "));
  Serial.print(channelIndices[0]);
  Serial.print(' ');
  Serial.print(channelIndices[1]);
  Serial.print(' ');
  Serial.println(channelIndices[2]);
#endif

  if (m_pSignalSource == 0) {
    SET_ERROR(Errors::OPERATION_NOT_SUPPORTED);
    color.red = color.green = color.blue = 0;
  } else {
    numChannels = m_pSignalSource->numChannels();

    if (channelIndices[0] >= numChannels) {
      SET_ERROR(Errors::INVALID_CHANNEL_INDEX);
      color.red = 0;
    } else {
      color.red = m_pSignalSource->filteredChannelValue(channelIndices[0]);
    }

    if (channelIndices[1] >= numChannels) {
      SET_ERROR(Errors::INVALID_CHANNEL_INDEX);
      color.green = 0;
    } else {
      color.green = m_pSignalSource->filteredChannelValue(channelIndices[1]);
    }

    if (channelIndices[2] >= numChannels) {
      SET_ERROR(Errors::INVALID_CHANNEL_INDEX);
      color.blue = 0;
    } else {
      color.blue = m_pSignalSource->filteredChannelValue(channelIndices[2]);
    }
  }

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

void CommandExecutor::handleJumpCommand() {
  unsigned long address = nextVarint();

#ifdef DEBUG
  Serial.print(F(" Arguments: "));
  Serial.println(address);
#endif

  if (address >= 0 && address < INT_MAX) {
    m_pBytecodeStore->seek(address);
    m_loopStack.clear();
  } else {
    SET_ERROR(Errors::INVALID_ADDRESS);
    stop();
  }
}

void CommandExecutor::handleLoopBeginCommand() {
  u8 iterations = nextByte();
  bytecode_location_t location = m_pBytecodeStore->tell();

  if (location == BYTECODE_LOCATION_NOWHERE) {
    SET_ERROR(Errors::OPERATION_NOT_SUPPORTED);
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
  setClockOriginToTimestamp(m_currentCommandStartTime);
}

void CommandExecutor::handleSetBlackCommand() {
  handleDelayByte();
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

  handleDelayByte();
  setColorOfLEDStrip(color);
}

void CommandExecutor::handleSetColorFromChannelsCommand() {
  rgb_color_t color;
  u8 numChannels;
  u8 channelIndices[3];

  channelIndices[0] = nextByte();
  channelIndices[1] = nextByte();
  channelIndices[2] = nextByte();

#ifdef DEBUG
  Serial.print(F(" Arguments: "));
  Serial.print(channelIndices[0]);
  Serial.print(' ');
  Serial.print(channelIndices[1]);
  Serial.print(' ');
  Serial.println(channelIndices[2]);
#endif

  if (m_pSignalSource == 0) {
    SET_ERROR(Errors::OPERATION_NOT_SUPPORTED);
    color.red = color.green = color.blue = 0;
  } else {
    numChannels = m_pSignalSource->numChannels();

    if (channelIndices[0] >= numChannels) {
      SET_ERROR(Errors::INVALID_CHANNEL_INDEX);
      color.red = 0;
    } else {
      color.red = m_pSignalSource->filteredChannelValue(channelIndices[0]);
    }

    if (channelIndices[1] >= numChannels) {
      SET_ERROR(Errors::INVALID_CHANNEL_INDEX);
      color.green = 0;
    } else {
      color.green = m_pSignalSource->filteredChannelValue(channelIndices[1]);
    }

    if (channelIndices[2] >= numChannels) {
      SET_ERROR(Errors::INVALID_CHANNEL_INDEX);
      color.blue = 0;
    } else {
      color.blue = m_pSignalSource->filteredChannelValue(channelIndices[2]);
    }
  }

  handleDelayByte();
  setColorOfLEDStrip(color);
}

void CommandExecutor::handleSetGrayCommand() {
  rgb_color_t color;

  color.red = color.green = color.blue = nextByte();

#ifdef DEBUG
  Serial.print(F(" Arguments: "));
  Serial.println(color.red);
#endif

  handleDelayByte();
  setColorOfLEDStrip(color);
}

void CommandExecutor::handleSetWhiteCommand() {
  handleDelayByte();
  setColorOfLEDStrip(COLOR_WHITE);
}

void CommandExecutor::handleSleepCommand() {
  handleDelayByte();
}

void CommandExecutor::handleTriggeredJumpCommand() {
  u8 triggerParams = nextByte();
  unsigned long address;
  u8 channelIndex;
  u8 edge;
  u8 willNeedAddress;
  Trigger* pTrigger;

  // First let's check whether we'll need an address in the next byte(s).
  // We need that if either the R or the F bit is set in the triggerParams
  if (triggerParams & 0x10) {
    if (triggerParams & 0x20) {
      edge = CHANGE;
    } else {
      edge = FALLING;
    }
  } else {
    if (triggerParams & 0x20) {
      edge = RISING;
    } else {
      edge = 0;
    }
  }
  willNeedAddress = (edge != 0);
  if (willNeedAddress) {
    address = nextVarint();
  }

  // Also extract the channel index
  channelIndex = triggerParams & 0x0F;

#ifdef DEBUG
  Serial.print(F(" Arguments: "));
  Serial.println(triggerParams);
  if (willNeedAddress) {
    Serial.println(address);
  }
#endif

  // Validate the address and send an error signal if it is invalid
  if (willNeedAddress && (address < 0 || address >= INT_MAX)) {
    SET_ERROR(Errors::INVALID_ADDRESS);
    stop();
  }

  // Find the trigger corresponding to the channel
  pTrigger = findTriggerForChannelIndex(channelIndex);
  if (pTrigger == 0) {
    SET_ERROR(Errors::NO_MORE_AVAILABLE_TRIGGERS);
    stop();
  }

  pTrigger->watchChannel(m_pSignalSource, channelIndex, edge);
  if (triggerParams & 0x40) {
    pTrigger->setOneShotMode();
  } else {
    pTrigger->setPermanentMode();
  }
}

void CommandExecutor::handleWaitUntilCommand() {
  unsigned long deadline = nextVarint();

#ifdef DEBUG
  Serial.print(F(" Arguments: "));
  Serial.println(deadline);
#endif

  delayExecutionUntil(deadline);
  m_cumulativeDurationSinceStart = absoluteToInternalTime(m_nextWakeupTime);
}
