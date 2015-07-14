/**
 * \file bytecode_first_test.h
 * \brief Test sequence for the transition types in ledctrl
 */

CMD_LOOP_BEGIN, 0,

CMD_FADE_TO_COLOR, 255,   0,   0, DURATION_BYTE(1), EASING_LINEAR,
CMD_FADE_TO_COLOR, 255, 255,   0, DURATION_BYTE(1), EASING_LINEAR,
CMD_FADE_TO_COLOR,   0, 255,   0, DURATION_BYTE(1), EASING_LINEAR,
CMD_FADE_TO_COLOR,   0, 255, 255, DURATION_BYTE(1), EASING_LINEAR,
CMD_FADE_TO_COLOR,   0,   0, 255, DURATION_BYTE(1), EASING_LINEAR,
CMD_FADE_TO_BLACK,                DURATION_BYTE(1), EASING_LINEAR,
CMD_SLEEP, DURATION_BYTE(2),

CMD_FADE_TO_COLOR, 255,   0,   0, DURATION_BYTE(1), EASING_IN_OUT_SINE,
CMD_FADE_TO_BLACK,                DURATION_BYTE(1), EASING_IN_OUT_SINE,
CMD_FADE_TO_COLOR,   0, 255,   0, DURATION_BYTE(1), EASING_IN_OUT_SINE,
CMD_FADE_TO_BLACK,                DURATION_BYTE(1), EASING_IN_OUT_SINE,
CMD_FADE_TO_COLOR,   0,   0, 255, DURATION_BYTE(1), EASING_IN_OUT_SINE,
CMD_FADE_TO_BLACK,                DURATION_BYTE(1), EASING_IN_OUT_SINE,
CMD_SLEEP, DURATION_BYTE(2),

CMD_FADE_TO_COLOR, 255,   0,   0, DURATION_BYTE(1), EASING_OUT_BOUNCE,
CMD_FADE_TO_BLACK,                DURATION_BYTE(1), EASING_OUT_CIRC,
CMD_FADE_TO_COLOR,   0, 255,   0, DURATION_BYTE(1), EASING_OUT_BOUNCE,
CMD_FADE_TO_BLACK,                DURATION_BYTE(1), EASING_OUT_CIRC,
CMD_FADE_TO_COLOR,   0,   0, 255, DURATION_BYTE(1), EASING_OUT_BOUNCE,
CMD_FADE_TO_BLACK,                DURATION_BYTE(1), EASING_OUT_CIRC,
CMD_SLEEP, DURATION_BYTE(2),

CMD_LOOP_END,

CMD_END