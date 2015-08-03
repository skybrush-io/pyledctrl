/**
 * \file trigger.h
 * \brief Trigger implementation for the bytecode executor.
 */

#ifndef TRIGGER_H
#define TRIGGER_H

#include "edge_detector.h"

class SignalSource;

/**
 * Enum that describes the set of actions that may happen when a trigger is fired.
 */
namespace TriggerActionType {
  enum Enum {
    RESUME,                 ///< Resume execution (if the trigger suspended execution)
    JUMP_TO_ADDRESS,        ///< Jump to a given address    
  };
};

/**
 * Struct that fully describes an action that may happen when a trigger is fired.
 */
typedef struct {
  TriggerActionType::Enum type;       ///< The type of the action
  union {
    uint16_t address;                 ///< The jump address for a JUMP_TO_ADDRESS action
  } arguments;
} TriggerAction;

/**
 * \brief Trigger implementation for the bytecode executor.
 * 
 * Bytecode executors may have up to a given number of triggers, where each
 * trigger is watching a signal source channel, and performs a jump instruction
 * in the bytecode to a given address when a rising or falling edge is detected
 * in the signal source.
 */
class Trigger {
private:
  /**
   * The signal source that the trigger is watching.
   */
  const SignalSource* m_pSignalSource;

  /**
   * The action to perform when the trigger is fired.
   */
  TriggerAction m_action;
  
  /**
   * The index of the channel in the signal source that the trigger is watching.
   */
  u8 m_channelIndex;
  
  /**
   * The edge detector that the trigger uses to process the signal.
   */
  EdgeDetector m_edgeDetector;

  /**
   * Whether the trigger is in one-shot mode.
   */
  bool m_oneShotMode;
  
public:
  /**
   * Constructor.
   */
  explicit Trigger();

  /**
   * Returns whether the trigger is active.
   */
  bool active() const {
    return m_pSignalSource != 0;
  } 

  /**
   * Returns the action to be executed by the trigger.
   */
  TriggerAction action() const {
    return m_action;
  }

  /**
   * Returns the index of the channel watched by this trigger.
   */
  u8 channelIndex() const {
    return m_channelIndex;
  }
  
  /**
   * Asks the trigger to check the state of the signal being watched (if any)
   * and fire if needed.
   * 
   * \return  \c true if the trigger fired, \c false otherwise
   */
  bool checkAndFireWhenNeeded();
  
  /**
   * Disables the trigger.
   */
  void disable();

  /**
   * Fires the trigger unconditionally.
   */
  void fire();

  /**
   * Sets the trigger to one-shot mode. Triggers in one-shot mode deactivate
   * themselves automatically after they fire.
   */
  void setOneShotMode();
  
  /**
   * Sets the trigger to permanent mode. Triggers in permanent mode stay
   * activated after they fire.
   */
  void setPermanentMode();
  
  /**
   * Asks the trigger to watch the given channel of the given signal source
   * and jump to the given address when a rising or falling edge is detected.
   * 
   * \param  signalSource  the signal source
   * \param  channelIndex  the index of the channel to watch
   * \param  edge          which edge to watch; may be one of \c RISING,
   *                       \c FALLING or \c CHANGE. These are built-in
   *                       Arduino constants.
   */
  void watchChannel(const SignalSource* signalSource, u8 channelIndex, u8 edge);
};

#endif
