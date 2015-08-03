/**
 * \file executor.h
 * Class for executing commands to control the LED strip.
 */

#ifndef EXECUTOR_H
#define EXECUTOR_H

#include "config.h"
#include "errors.h"
#include "led_strip.h"
#include "loop_stack.h"
#include "transition.h"
#include "trigger.h"
#include "types.h"

class BytecodeStore;
class LED;
class SignalSource;

/**
 * Executes commands that control the attached LED strip.
 */
class CommandExecutor {
private:
  /**
   * The LED strip that the executor will control.
   */
  LEDStrip* m_pLEDStrip;

  /**
   * Object managing access to the bytecode being executed.
   */
  BytecodeStore* m_pBytecodeStore;

  /**
   * Object managing access to the values of the signal channels (typically from a remote controller).
   */
  SignalSource* m_pSignalSource;
  
  /**
   * Pointer to the current location within the bytecode.
   */
  const u8* m_pNextCommand;

  /**
   * Whether the bytecode being executed has reached the end of the 
   * program.
   */
  bool m_ended;

  /**
   * Loop stack holding pointers to the beginnings of the active loops and
   * the number of iterations left.
   */
  LoopStack m_loopStack;

  /**
   * Time when the execution of the current command has started. Used to
   * calculate the next wakeup time.
   */
  unsigned long m_currentCommandStartTime;

  /**
   * Time when the internal clock of the executor was reset the last time,
   * according to the internal clock of the Arduino.
   * 
   * Note that the internal clock of the executor is not the same as the
   * internal clock of the Arduino; the offset between them is exactly
   * equal to the value of this variable.
   */
  unsigned long m_lastClockResetTime;

  /**
   * Time when the executor is supposed to execute the next command.
   */
  unsigned long m_nextWakeupTime;

  /**
   * Auxiliary structure for handling color transitions on the LED strip.
   * Maintains the color-related state variables of the current transition.
   */
  LEDStripColorFader m_ledStripFader;
  
  /**
   * Auxiliary structure for handling color transitions on the LED strip.
   * Maintains the time-related state variables of the current transition.
   */
  Transition<LEDStripColorFader> m_transition;

  /**
   * Auxiliary structure for holding information about the triggers in the code.
   */
  Trigger m_triggers[MAX_TRIGGER_COUNT];
  
public:
  /**
   * \brief Constructor.
   * 
   * \param  pLEDStrip  the LED strip that the executor will control
   */
  explicit CommandExecutor(LEDStrip* pLEDStrip=0);

  /**
   * \brief Returns the bytecode store that the executor will use.
   */
  BytecodeStore* bytecodeStore() const {
    return m_pBytecodeStore;
  }
  
  /**
   * \brief Returns the value of the internal clock of the executor.
   * 
   * This is equal to the number of milliseconds elapsed since the last reset
   * of the internal clock or the start of the executor, whichever was
   * later.
   */
  unsigned long clock() const {
    return millis() - m_lastClockResetTime;
  }
  
  /**
   * \brief Rewinds the execution to the start of the current bytecode.
   */
  void rewind();

  /**
   * \brief Resets the internal clock of the bytecode executor.
   */
  void resetClock() {
    m_lastClockResetTime = m_currentCommandStartTime;
  }

  /**
   * \brief Sets the bytecode store that the executor will use.
   */
  void setBytecodeStore(BytecodeStore* pBytecodeStore) {
    m_pBytecodeStore = pBytecodeStore;
    rewind();
  }

  /**
   * \brief Sets the signal source that the executor will use.
   */
  void setSignalSource(SignalSource* pSignalSource) {
    m_pSignalSource = pSignalSource;
  }
  
  /**
   * \brief Returns the signal source that the executor will use.
   */
  SignalSource* signalSource() const {
    return m_pSignalSource;
  }
  
  /**
   * \brief This function must be called repeatedly from the main loop
   *        of the sketch to keep the execution flowing.
   *        
   * \return the time according to the internal clock of the Arduino when
   *         the next command is to be executed.
   */
  unsigned long step();
  
  /**
   * \brief Stops the execution of the program.
   */
  void stop();
  
private:
  /**
   * \brief Checks and fires the active triggers if needed.
   */
  void checkAndFireTriggers();
  
  /**
   * \brief Delays the execution of the commands for the given duration,
   *        relative to the current time.
   *        
   * This function does \em not make the Arduino sleep, it simply sets an
   * internal variable in the executor that suspends the execution of
   * commands until the given amount of time has passed.
   * 
   * \param  duration  the delay duration, in milliseconds
   */
  void delayExecutionFor(unsigned long duration);
  
  /**
   * \brief Delays the execution of the commands until the internal clock
   *        of the \em Arduino reaches the given value.
   *        
   * This function does \em not make the Arduino sleep, it simply sets an
   * internal variable in the executor that suspends the execution of
   * commands until the given clock value is reached.
   * 
   * \param  ms  the desired value of the internal clock to wait for
   */
  void delayExecutionUntil(unsigned long ms);

  /**
   * \brief Executes the action prescribed by the given trigger.
   * 
   * This function must be called after the trigger fired.
   */
  void executeActionOfTrigger(const Trigger* trigger);
  
  /**
   * \brief Executes the next command from the bytecode.
   * 
   * This function is a no-op if the program has ended.
   */
  void executeNextCommand();

  /**
   * \brief Fades the color of the LED strip to the given color.
   * Common code segment for the different \c "handleFadeTo..." commands.
   * 
   * \param  color       the target color
   */
  void fadeColorOfLEDStrip(rgb_color_t color);

  /**
   * \brief Finds a trigger that will handle the given channel.
   * 
   * When the channel already had a previous trigger, this function
   * will return the same trigger. When the channel did not have a trigger
   * before, this function will find a free trigger slot and return
   * that. When there are no more free trigger slots, the function
   * returns NULL.
   * 
   * \param   channelIndex  index of the channel
   * \return  pointer to the trigger slot that will handle the given channel,
   *          or \c NULL if there are no more available trigger slots.
   */
  Trigger* findTriggerForChannelIndex(u8 channelIndex);
  
  /**
   * \brief Interprets the next byte from the bytecode as a duration and
   *        sets the next wakeup time of the executor appropriately. 
   *        
   * \return  the parsed duration
   */
  unsigned long handleDelayByte();

  /**
   * \brief Interprets the next byte from the bytecode as an easing mode.
   *        
   * \return  the parsed easing mode
   */
  EasingMode handleEasingModeByte();
  
  /**
   * \brief Handles the execution of \c CMD_FADE_TO_BLACK commands.
   */
  void handleFadeToBlackCommand();
        
  /**
   * \brief Handles the execution of \c CMD_FADE_TO_COLOR commands.
   */
  void handleFadeToColorCommand();
        
  /**
   * \brief Handles the execution of \c CMD_FADE_TO_COLOR_FROM_CHANNELS commands.
   */
  void handleFadeToColorFromChannelsCommand();

  /**
   * \brief Handles the execution of \c CMD_FADE_TO_GRAY commands.
   */
  void handleFadeToGrayCommand();

  /**
   * \brief Handles the execution of \c CMD_FADE_TO_WHITE commands.
   */
  void handleFadeToWhiteCommand();

  /**
   * \brief Handles the execution of \c CMD_JUMP commands.
   */
  void handleJumpCommand();
  
  /**
   * \brief Handles the execution of \c CMD_LOOP_BEGIN commands.
   */
  void handleLoopBeginCommand();

  /**
   * \brief Handles the execution of \c CMD_LOOP_END commands.
   */
  void handleLoopEndCommand();

  /**
   * \brief Handles the execution of \c CMD_RESET_CLOCK commands.
   */
  void handleResetClockCommand();
  
  /**
   * \brief Handles the execution of \c CMD_SET_BLACK commands.
   */
  void handleSetBlackCommand();

  /**
   * \brief Handles the execution of \c CMD_SET_COLOR commands.
   */
  void handleSetColorCommand();

  /**
   * \brief Handles the execution of \c CMD_SET_COLOR_FROM_CHANNELS commands.
   */
  void handleSetColorFromChannelsCommand();

  /**
   * \brief Handles the execution of \c CMD_SET_GRAY commands.
   */
  void handleSetGrayCommand();

  /**
   * \brief Handles the execution of \c CMD_SET_WHITE commands.
   */
  void handleSetWhiteCommand();

  /**
   * \brief Handles the execution of \c CMD_SLEEP commands.
   */
  void handleSleepCommand();

  /**
   * \brief Handles the execution of \c CMD_TRIGGERED_JUMP commands.
   */
  void handleTriggeredJumpCommand();
  
  /**
   * \brief Handles the execution of \c CMD_WAIT_UNTIL commands.
   */
  void handleWaitUntilCommand();
  
  /**
   * \brief Reads the next byte from the bytecode and advances the
   *        execution pointer.
   */
  u8 nextByte();

  /**
   * \brief Reads the next byte from the bytecode, interprets it as a 
   *        duration and advances the execution pointer.
   */
  unsigned long nextDuration();
  
  /**
   * \brief Reads the next varint from the bytecode and advances the
   *        execution pointer.
   */
  unsigned long nextVarint();

  /**
   * \brief Sets the color of the LED strip to the given color.
   * Contains common code for the different \c "handleSetColor..."
   * functions.
   */
  void setColorOfLEDStrip(rgb_color_t color);
};

#endif
