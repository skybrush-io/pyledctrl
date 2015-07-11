/**
 * \file bytecode_first_test.h
 * \brief Simple test sequence for ledctrl
 */
 
/* White-off-white-off for one second each */
CMD_SET_GRAY,  255, DURATION_BYTE(1),
CMD_SET_GRAY,    0, DURATION_BYTE(1),
CMD_SET_WHITE, DURATION_BYTE(1),
CMD_SET_BLACK, DURATION_BYTE(0),
CMD_SLEEP,     DURATION_BYTE(1),

/* Loop starts here; it will be run five times */
CMD_LOOP_BEGIN,  5,

/* Red-green-blue-off for one second each */
CMD_SET_COLOR, 255,   0,   0,   DURATION_BYTE(1),
CMD_SET_COLOR,   0, 255,   0,   DURATION_BYTE(1),
CMD_SET_COLOR,   0,   0, 255,   DURATION_BYTE(1),
CMD_SET_COLOR,   0,   0,   0,   DURATION_BYTE(1),

/* Red-green-blue-off for 0.5 seconds each */
CMD_SET_COLOR, 255,   0,   0,   DURATION_BYTE(0.5),
CMD_SET_COLOR,   0, 255,   0,   DURATION_BYTE(0.5),
CMD_SET_COLOR,   0,   0, 255,   DURATION_BYTE(0.5),
CMD_SET_COLOR,   0,   0,   0,   DURATION_BYTE(0.5),

/* Loop ends here */
CMD_LOOP_END,

/* At this point we should be at 34 seconds.
 * Wait until we reach 40 seconds = 40000 msec.
 * 40000 = 10011100 01000000, which ends up being
 * 11000000 10111000 00000010 in varint encoding */
CMD_WAIT_UNTIL, 192, 184, 2,

/* Rapid flash at the end */
CMD_LOOP_BEGIN, 16,
CMD_SET_WHITE, DURATION_BYTE(0.125),
CMD_SET_BLACK, DURATION_BYTE(0.125),
CMD_LOOP_END,
CMD_SET_WHITE, DURATION_BYTE(2),
CMD_SET_BLACK,

/* Program end marker */
CMD_END
