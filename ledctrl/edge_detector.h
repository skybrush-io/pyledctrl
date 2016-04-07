/**
 * \file edge_detector.h
 * \brief Edge detector class with filtering and debouncing capabilities.
 */

#ifndef EDGE_DETECTOR_H
#define EDGE_DETECTOR_H

#include "types.h"

/**
 * State constants for the edge detector class.
 */
namespace EdgeDetectorState {
  enum Enum {
    START = 0,                     ///< Signal state unknown yet
    SIGNAL_LOW = 1,                ///< Signal is in the LOW state
    SIGNAL_HIGH = 3,               ///< Signal is in the HIGH state
    SIGNAL_RISING = 5,             ///< Signal is rising from LOW to HIGH
    SIGNAL_FALLING = 7             ///< Signal is falling from HIGH to LOW
  };
}

class EdgeDetector;

/**
 * Typedef for a callback function of an edge detector.
 */
typedef void EdgeDetectorCallback(EdgeDetector* detector, long time, void* data);

/**
 * Structure holding the callback functions of an edge detector.
 */
typedef struct {
  /**
   * Callback function that will be called for each detected rising edge.
   */
  EdgeDetectorCallback* rising;

  /**
   * Callback function that will be called for each detected falling edge.
   */
  EdgeDetectorCallback* falling;
} EdgeDetectorCallbacks;

/**
 * \brief Edge detector class with filtering and debouncing capabilities.
 *
 * Edge detectors work with analog signals represented by bytes in the range
 * 0 to 255. The analog signal is a noisy representation an underlying digital
 * (binary) signal, which may be either in its LOW (0) or HIGH (255) state. The
 * goal of the edge detector is to reliably decide whether the underlying
 * digital signal is in its LOW or HIGH state by looking at samples of the
 * analog signal. It also provides callback functions for transitions from the
 * LOW to the HIGH state and vice versa.
 *
 * The full range of the analog signal (0-255) is divided into three
 * sub-ranges: LOW, MID and HIGH. The LOW range spans from zero (inclusive) to
 * \c m_midRangeStart (exclusive), while the HIGH range spans from \c
 * m_midRangeEnd (inclusive) to 255 (inclusive). The MID range spans the
 * remaining range (from \c m_midRangeStart (inclusive) to \c m_midRangeEnd
 * (exclusive). The default values are \c m_midRangeStart = 64 and \c
 * m_midRangeEnd = 192, which should be satisfactory for most applications.
 * The analog signal is considered to represent a digital LOW when it is in the
 * LOW range and is considered to represent a digital HIGH when it is in the
 * HIGH range. When the analog signal is in the MID range, it is assumed to
 * represent the \em last digital HIGH or LOW state.
 *
 * Additionally, the edge detector supports a debouncing interval in its
 * \c m_debounceMs variable. When a transition from \c LOW to \c HIGH or from
 * \c HIGH to \c LOW is detected, further transitions will be ignored for
 * up to \c m_debounceMs milliseconds (the signal is assumed to stay in the
 * same state for this period). Normal operation is resumed after at least
 * \c m_debounceMs milliseconds have passed.
 */
class EdgeDetector {
private:
  /**
   * Start of the \c MID range (inclusive).
   */
  u8 m_midRangeStart;

  /**
   * End of the \c MID range (exclusive).
   */
  u8 m_midRangeEnd;

  /**
   * Debouncing interval in milliseconds. Use zero to disable debouncing.
   */
  u16 m_debounceMs;

  /**
   * Timestamp of the last transition. Used for debouncing.
   */
  long m_lastTransition;

  /**
   * State of the edge detector.
   */
  EdgeDetectorState::Enum m_state;

public:
  /**
   * Callback functions of the edge detector.
   */
  EdgeDetectorCallbacks callbacks;

  /**
   * Additional data pointer to pass to the callbacks.
   */
  void* callbackData;
  
  /**
   * Constructor.
   *
   * \param  midRangeStart  the start of the \c MID range (inclusive)
   * \param  midRangeEnd    the end of the \c MID range (exclusive)
   * \param  debounceMs     the length of the debouncing interval.
   */
  explicit EdgeDetector(u8 midRangeStart=64, u8 midRangeEnd=192, u16 debounceMs=0)
    : m_midRangeStart(midRangeStart), m_midRangeEnd(midRangeEnd),
    m_debounceMs(debounceMs), callbackData(0) {
    reset();
  }

  /**
   * Disables the debouncing filter.
   */
  void disableDebouncing() {
    enableDebouncing(0);
  }

  /**
   * Sets the debouncing interval.
   */
  void enableDebouncing(uint16_t debounceMs) {
    m_debounceMs = debounceMs;
  }

  /**
   * Feeds the edge detector with the current state of the analog signal.
   *
   * \param  signal  the current state of the analog signal
   * \return whether at least one callback function was fired
   */
  bool feedAnalogSignal(u8 signal) {
    return feedAnalogSignal(signal, millis());
  }

  /**
   * Feeds the edge detector with the state of the analog signal at the given
   * time instant.
   *
   * The function assumes that the time instant being used here will be
   * monotonously increasing.
   *
   * \param  signal  the current state of the analog signal
   * \param  time    the timestamp
   * \return whether at least one callback function was fired
   */
  bool feedAnalogSignal(u8 signal, long time) {
    bool result = false;
    
    if (m_debounceMs > 0 && m_lastTransition + m_debounceMs < time) {
      // Debounce filter active; do nothing.
      return false;
    }

    switch (m_state) {
      case EdgeDetectorState::START:
        // Initial state; we just move to LOW or HIGH if we get the
        // first value from the LOW or the HIGH range. No rising or
        // falling edge is assumed.
        if (signal < m_midRangeStart) {
          m_state = EdgeDetectorState::SIGNAL_LOW;
        } else if (signal >= m_midRangeEnd) {
          m_state = EdgeDetectorState::SIGNAL_HIGH;
        }
        break;

      case EdgeDetectorState::SIGNAL_LOW:
        if (signal >= m_midRangeEnd) {
          m_state = EdgeDetectorState::SIGNAL_HIGH;
          result = handleRisingEdge(time);
        }
        break;

      case EdgeDetectorState::SIGNAL_RISING:
        // TODO: not implemented yet.
        reset();
        break;

      case EdgeDetectorState::SIGNAL_HIGH:
        if (signal < m_midRangeStart) {
          m_state = EdgeDetectorState::SIGNAL_LOW;
          result = handleFallingEdge(time);
        }
        break;

      case EdgeDetectorState::SIGNAL_FALLING:
        // TODO: not implemented yet.
        reset();
        break;

      default:
        // Invalid state; let's just reset ourselves.
        reset();
        break;
    }

    return result;
  }

  /**
   * Resets the edge detector to its ground state.
   */
  void reset() {
    m_lastTransition = 0;
    m_state = EdgeDetectorState::START;
  }

  /**
   * Returns the current (predicted) state of the digital signal.
   *
   * \return  0 if the signal is assumed to be \c LOW, 1 if the signal is
   *          assumed to be \c HIGH, -1 if the signal state is not known
   *          yet
   */
  s8 value() const {
    return m_state == EdgeDetectorState::SIGNAL_HIGH ? 1 : (m_state == EdgeDetectorState::SIGNAL_LOW ? 0 : -1);
  }

private:
  /**
   * Handles a falling edge detected on the input signal at the given time.
   * 
   * \return whether the falling edge clalback function was called. 
   */
  bool handleFallingEdge(long time) {
    m_lastTransition = time;
    if (callbacks.falling != 0) {
      callbacks.falling(this, time, callbackData);
      return true;
    }
    return false;
  }

  /**
   * Handles a rising edge detected on the input signal at the given time.
   */
  bool handleRisingEdge(long time) {
    m_lastTransition = time;
    if (callbacks.rising != 0) {
      callbacks.rising(this, time, callbackData);
      return true;
    }
    return false;
  }
};

#endif

