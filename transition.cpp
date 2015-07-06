#include "transition.h"

/* The following functions are translated from:
 * https://github.com/warrenm/AHEasing/blob/master/AHEasing/easing.c
 */

transition_progress_t easing_func_linear(transition_progress_t p) {
  return p;
}

transition_progress_t easing_func_in_sine(transition_progress_t p) {
  return sin((p-1) * M_PI_2) + 1;
}

transition_progress_t easing_func_out_sine(transition_progress_t p) {
  return sin(p * M_PI_2);
}

transition_progress_t easing_func_in_out_sine(transition_progress_t p) {
  return 0.5 * (1 - cos(p * M_PI));
}

transition_progress_t easing_func_in_quad(transition_progress_t p) {
  return p*p;
}

transition_progress_t easing_func_out_quad(transition_progress_t p) {
  return p*p;
}

transition_progress_t easing_func_in_out_quad(transition_progress_t p) {
  return (p < 0.5) ? 2*p*p : (-2*p*p + 4*p - 1);
}

transition_progress_t easing_func_in_cubic(transition_progress_t p) {
  return pow(p, 3);
}

transition_progress_t easing_func_out_cubic(transition_progress_t p) {
  return pow(p-1, 3) + 1;
}

transition_progress_t easing_func_in_out_cubic(transition_progress_t p) {
  return (p < 0.5) ? 4*pow(p, 3) : (0.5*pow(2*p-2, 3) + 1);
}

transition_progress_t easing_func_in_quart(transition_progress_t p) {
  return pow(p, 4);
}

transition_progress_t easing_func_out_quart(transition_progress_t p) {
  return -pow(p-1, 4) + 1;
}

transition_progress_t easing_func_in_out_quart(transition_progress_t p) {
  return (p < 0.5) ? 8*pow(p, 4) : (-8*pow(p, 4) + 1);
}

transition_progress_t easing_func_in_quint(transition_progress_t p) {
  return pow(p, 5);
}

transition_progress_t easing_func_out_quint(transition_progress_t p) {
  return pow(p-1, 5) + 1;
}

transition_progress_t easing_func_in_out_quint(transition_progress_t p) {
  return (p < 0.5) ? 16*pow(p, 5) : (0.5*pow(2*p-2, 5) + 1);
}

transition_progress_t easing_func_in_circ(transition_progress_t p) {
  return 1 - sqrt(1 - p*p);
}

transition_progress_t easing_func_out_circ(transition_progress_t p) {
  return sqrt((2-p) * p);
}

transition_progress_t easing_func_in_out_circ(transition_progress_t p) {
  return (p < 0.5) ? (0.5 * (1-sqrt(1-4*p*p))) : (0.5*(sqrt(-((2*p)-3)*((2*p)-1))+1));
}

transition_progress_t easing_func_in_expo(transition_progress_t p) {
  return p <= 0 ? p : pow(2, 10*(p-1));
}

transition_progress_t easing_func_out_expo(transition_progress_t p) {
  return p >= 1 ? p : (1 - pow(2, -10*p));
}

transition_progress_t easing_func_in_out_expo(transition_progress_t p) {
  if (p <= 0 || p >= 1) {
    return p;
  } else {
    return (p < 0.5) ? (0.5 * pow(2, (20*p)-10)) : (-0.5 * pow(2, (-20*p)+10) + 1);
  }
}

transition_progress_t easing_func_in_elastic(transition_progress_t p) {
  return sin(13 * M_PI_2 * p) * pow(2, 10 * (p-1));
}

transition_progress_t easing_func_out_elastic(transition_progress_t p) {
  return sin(-13 * M_PI_2 * (p+1)) * pow(2, -10*p) + 1;
}

transition_progress_t easing_func_in_out_elastic(transition_progress_t p) {
  if (p < 0.5) {
    return 0.5 * sin(13 * M_PI_2 * (2 * p)) * pow(2, 10 * ((2 * p) - 1));
  } else {
    return 0.5 * (sin(-13 * M_PI_2 * ((2 * p - 1) + 1)) * pow(2, -10 * (2 * p - 1)) + 2);
  }
}

transition_progress_t easing_func_in_back(transition_progress_t p) {
  return pow(p, 3) - p * sin(p * M_PI);
}

transition_progress_t easing_func_out_back(transition_progress_t p) {
  transition_progress_t f = (1 - p);
  return 1 - (pow(f, 3) - f * sin(f * M_PI));
}

transition_progress_t easing_func_in_out_back(transition_progress_t p) {
  if (p < 0.5) {
    transition_progress_t f = 2 * p;
    return 0.5 * (pow(f, 3) - f * sin(f * M_PI));
  } else {
    transition_progress_t f = (1 - (2*p - 1));
    return 0.5 * (1 - (pow(f, 3) - f * sin(f * M_PI))) + 0.5;
  }
}

transition_progress_t easing_func_out_bounce(transition_progress_t p) {
  if (p < 4/11.0) {
    return (121 * p * p)/16.0;
  } else if (p < 8/11.0) {
    return (363/40.0 * p * p) - (99/10.0 * p) + 17/5.0;
  } else if (p < 9/10.0) {
    return (4356/361.0 * p * p) - (35442/1805.0 * p) + 16061/1805.0;
  } else {
    return (54/5.0 * p * p) - (513/25.0 * p) + 268/25.0;
  }
}

transition_progress_t easing_func_in_bounce(transition_progress_t p) {
  return 1 - easing_func_out_bounce(1 - p);
}

transition_progress_t easing_func_in_out_bounce(transition_progress_t p) {
  if (p < 0.5) {
    return 0.5 * easing_func_in_bounce(p*2);
  } else {
    return 0.5 * easing_func_out_bounce(p * 2 - 1) + 0.5;
  }
}

const easing_function_t *EASING_FUNCTIONS[NUM_EASING_FUNCTIONS] = {
  easing_func_linear,
  easing_func_in_sine,
  easing_func_out_sine,
  easing_func_in_out_sine,
  easing_func_in_quad,
  easing_func_out_quad,
  easing_func_in_out_quad,
  easing_func_in_cubic,
  easing_func_out_cubic,
  easing_func_in_out_cubic,
  easing_func_in_quart,
  easing_func_out_quart,
  easing_func_in_out_quart,
  easing_func_in_quint,
  easing_func_out_quint,
  easing_func_in_out_quint,
  easing_func_in_expo,
  easing_func_out_expo,
  easing_func_in_out_expo,
  easing_func_in_circ,
  easing_func_out_circ,
  easing_func_in_out_circ,
  easing_func_in_back,
  easing_func_out_back,
  easing_func_in_out_back,
  easing_func_in_elastic,
  easing_func_out_elastic,
  easing_func_in_out_elastic,
  easing_func_in_bounce,
  easing_func_out_bounce,
  easing_func_in_out_bounce
};

