/**
 * \file trigger.h
 * \brief Trigger implementation for the bytecode executor.
 */

#ifndef TRIGGER_H
#define TRIGGER_H

#include "edge_detector.h"

class SignalSource;

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
   * The index of the channel in the signal source that the trigger is watching.
   */
  u8 m_channelIndex;
  
  /**
   * The edge detector that the trigger uses to process the signal.
   */
  EdgeDetector m_edgeDetector;

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
   * Asks the trigger to check the state of the signal being watched (if any)
   * and fire if needed.
   */
  void checkAndFireWhenNeeded();
  
  /**
   * Disables the trigger.
   */
  void disable();

  /**
   * Fires the trigger unconditionally.
   */
  void fire();
  
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
