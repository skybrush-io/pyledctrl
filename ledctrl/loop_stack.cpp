#include "loop_stack.h"

bool LoopStack::begin(bytecode_location_t location, u8 iterations) {
  if (m_pTopItem >= m_items + MAX_LOOP_DEPTH) {
    return false;
  }

  m_pTopItem++;
  m_numLoops++;
  m_pTopItem->start = location;
  m_pTopItem->iterationsLeftPlusOne = iterations;
  /* Yes, the line above is correct. If this is an infinite loop, we simply
   * store zero. If this is not an infinite loop, we would need to store
   * iterations+1, but since we start the loop immediately, we can decrease
   * it by 1.
   */

  return true;
}

const bytecode_location_t LoopStack::end() {
  u8 iterationsLeftPlusOne;
  
  if (m_pTopItem != 0) {
    iterationsLeftPlusOne = m_pTopItem->iterationsLeftPlusOne;
    if (iterationsLeftPlusOne == 0) {
      /* This is an infinite loop */
      return m_pTopItem->start;
    } else if (iterationsLeftPlusOne == 1) {
      /* Last iteration */
      m_pTopItem->iterationsLeftPlusOne = 0;
      m_pTopItem = (m_pTopItem == m_items) ? 0 : m_pTopItem-1;
      m_numLoops--;
      return BYTECODE_LOCATION_NOWHERE;
    } else {
      /* We still have some iterations */
      m_pTopItem->iterationsLeftPlusOne--;
      return m_pTopItem->start;
    }
  } else {
    return BYTECODE_LOCATION_NOWHERE;
  }
}

