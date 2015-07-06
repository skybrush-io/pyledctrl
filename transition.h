/**
 * \file transition.h
 * \brief Color transition handling on a LED strip.
 */

#ifndef TRANSITION_H
#define TRANSITION_H

#include "config.h"

/**
 * \brief Defines the floating-point type that transitions will use.
 * 
 * Switch this to \c double for extra precision (though this should not
 * be needed).
 */
typedef float transition_progress_t;

/**
 * \brief Easing modes for transitions.
 * 
 * See http://easings.net for more information about the modes being used here.
 */
typedef enum {
  EASING_LINEAR,
  EASING_IN_SINE,
  EASING_OUT_SINE,
  EASING_IN_OUT_SINE,
  EASING_IN_QUAD,
  EASING_OUT_QUAD,
  EASING_IN_OUT_QUAD,
  EASING_IN_CUBIC,
  EASING_OUT_CUBIC,
  EASING_IN_OUT_CUBIC,
  EASING_IN_QUART,
  EASING_OUT_QUART,
  EASING_IN_OUT_QUART,
  EASING_IN_QUINT,
  EASING_OUT_QUINT,
  EASING_IN_OUT_QUINT,
  EASING_IN_EXPO,
  EASING_OUT_EXPO,
  EASING_IN_OUT_EXPO,
  EASING_IN_CIRC,
  EASING_OUT_CIRC,
  EASING_IN_OUT_CIRC,
  EASING_IN_BACK,
  EASING_OUT_BACK,
  EASING_IN_OUT_BACK,
  EASING_IN_ELASTIC,
  EASING_OUT_ELASTIC,
  EASING_IN_OUT_ELASTIC,
  EASING_IN_BOUNCE,
  EASING_OUT_BOUNCE,
  EASING_IN_OUT_BOUNCE,
  NUM_EASING_FUNCTIONS
} EasingMode;

/**
 * \brief Typedef for easing functions.
 */
typedef transition_progress_t easing_function_t(transition_progress_t);

/**
 * \brief Mapping from easing modes to the corresponding easing functions.
 */
extern const easing_function_t *EASING_FUNCTIONS[NUM_EASING_FUNCTIONS];

/**
 * \brief Encapsulates information about a color transition in progress on a LED strip.
 * 
 * \tparam  TransitionHandler  a function that will be called with a single floating-point
 *             value between 0 and 1 from the \c step() method. The value
 *             corresponds to the progress of the transition after the
 *             easing function has been applied.
 */
template <typename TransitionHandler>
class Transition {
private:
  /**
   * Whether the transition is currently active.
   */
  bool m_active;

  /**
   * The start time of the transition.
   */
  unsigned long m_start;

  /**
   * The duration of the transition.
   */
  unsigned long m_duration;

  /**
   * The easing mode of the transition.
   */
  EasingMode m_easingMode;
  
public:
  /**
   * Constructor. Creates an inactive transition.
   */
  explicit Transition(): m_active(false), m_easingMode(EASING_LINEAR) {}

  /**
   * Returns whether the transition is currently active.
   */
  bool active() const {
    return m_active;
  }
  
  /**
   * Returns the current easing mode of the transition.
   */
  EasingMode easingMode() const {
    return m_easingMode;
  }

  /**
   * \brief Returns the progress of the transition as a value between 0 and 1, \em before
   * applying the easing function.
   */
  transition_progress_t progressPreEasing() const {
    return progressPreEasing(millis());
  }

  /**
   * \brief Returns the progress of the transition \em before applying the easing function.
   * 
   * \param  clock  the value of the internal clock
   * \return the progress of the transition expressed as a value between 0 and 1.
   */
  transition_progress_t progressPreEasing(unsigned long clock) const {
    transition_progress_t result;
    
    if (clock < m_start) {
      return 0;
    } else {
      clock -= m_start;
      result = ((transition_progress_t)clock) / m_duration;
      return result > 1 ? 1 : result;
    }
  }
  
  /**
   * \brief Returns the progress of the transition \em after applying the easing function.
   * 
   * Note that for some easing functions, the progress value can be negative or larger
   * than 1 for certain times.
   */
  transition_progress_t progressPostEasing() const {
    return progressPostEasing(millis());
  }
  
  /**
   * \brief Returns the progress of the transition \em after applying the easing function.
   * 
   * Note that for some easing functions, the progress value can be negative or larger
   * than 1 for certain times.
   * 
   * \param  clock  the value of the internal clock
   */
  transition_progress_t progressPostEasing(unsigned long clock) const {
    return EASING_FUNCTIONS[m_easingMode](progressPreEasing(clock));
  }
  
  /**
   * Sets the current easing mode of the transition.
   */
  void setEasingMode(EasingMode value) {
    m_easingMode = value;
  }

  /**
   * \brief Starts a transition with the given duration.
   * 
   * \param  duration   the duration of the transition
   */
  void start(unsigned long duration) {
    start(millis(), duration);
  }

  /**
   * Starts a transition with the given duration and start time.
   * 
   * \param  duration   the duration of the transition
   * \param  startTime  the start time of the transition.
   */
  void start(unsigned long duration, unsigned long startTime) {
    m_start = startTime;
    m_duration = duration;
    m_active = true;
  }

  /**
   * Makes a step in the transition.
   * 
   * \param  handler  the transition handler to call with the post-easing
   *                  progress of the transition
   * \return \c true if the transition shall continue, \c false if
   *         it has ended.
   */
  bool step(const TransitionHandler& handler) {
    return step(handler, millis());
  }
  
  /**
   * Makes a step in the transition, assuming that the internal
   * clock is at the given time.
   * 
   * \param  handler  the transition handler to call with the post-easing
   *                  progress of the transition
   * \param  clock  the time on the internal clock
   * \return \c true if the transition shall continue, \c false if
   *         it has ended.
   */
  bool step(const TransitionHandler& handler, unsigned long clock) {
    transition_progress_t progress = progressPreEasing(clock);
    transition_progress_t transformedProgress = EASING_FUNCTIONS[m_easingMode](progress);
    
    handler(transformedProgress);

    m_active = progress < 1;
    return m_active;
  }
};

/**
 * \brief Transition handler that simply prints the current transition 
 *        progress and the current clock to the serial console when
 *        we are in debug mode.
 */
struct DebugTransitionHandler {
  void operator()(transition_progress_t progress) const {
#ifdef DEBUG
    Serial.print("[");
    Serial.print(millis());
    Serial.print(" ms] transition progress: ");
    Serial.println(progress);
#endif
  }
};

#endif
