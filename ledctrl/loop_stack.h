/**
 * \file loop_stack.h
 * 
 * Implementation of a stack that is used for loop management in the bytecode.
 */

#ifndef LOOP_STACK_H
#define LOOP_STACK_H

#include "config.h"

/**
 * \brief Holds information about a single loop in a loop stack.
 */
typedef struct {
  const u8* start;  /**< Pointer to the first instruction of the body of the loop */

  /**
   * Number of iterations left for the current loop plus one, or zero of the loop
   * is infinite.
   */
  u8 iterationsLeftPlusOne;
} LoopStackItem;

/**
 * \brief Stack holding pointers to the starts of the loops in the bytecode and the
 * number of iterations left for these loops.
 */
class LoopStack {
private:
  /**
   * The items in the loop stack.
   */
  LoopStackItem m_items[MAX_LOOP_DEPTH];

  /**
   * Number of active loops in the loop stack.
   */
  u8 m_numLoops;
  
  /**
   * Pointer to the topmost item in the loop stack.
   */
  LoopStackItem* m_pTopItem;

public:
  /**
   * Constructs an empty loop stack.
   */
  LoopStack() {
    clear();
  }

  /**
   * Asks the loop stack to start a new loop at the given location with the given
   * number of iterations.
   * 
   * \param  location    the first instruction of the loop
   * \param  iterations  the number of iterations. Zero means an infinite loop.
   * 
   * \return \c true if the operation was successful, \c false if the loop stack
   *         is full
   */
  bool begin(const u8* location, u8 iterations);
  
  /**
   * Asks the loop stack to start an infinite loop at the given location.
   */
  void beginInfinite(const u8* location) {
    begin(location, 0);
  }

  /**
   * Removes all the items from the loop stack.
   */
  void clear() {
    m_pTopItem = 0;
    m_numLoops = 0;
  }
  
  /**
   * Notifies the loop stack that an end of loop marker was reached in the
   * bytecode. The loop stack then either returns the starting address of
   * the innermost loop if it has any iterations left, or returns null to
   * indicate that the execution can proceed as normal.
   * 
   * \return  the starting address of the innermost loop if it has any
   *          iterations left, null otherwise
   */
  const u8* end();

  /**
   * Returns the number of active loops in the stack.
   */
  u8 size() const {
    return m_numLoops;
  }
};

#endif
