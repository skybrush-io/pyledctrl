/**
 * \file bytecode_first_test.h
 * \brief Simple test sequence for ledctrl
 */
 
static const u8 bytecode[] = {
  /* White-off-white-off for one second each */
  CMD_SET_GRAY,  255, 50,
  CMD_SET_GRAY,    0, 50,
  CMD_SET_WHITE, 50,
  CMD_SET_BLACK, 0,
  CMD_SLEEP,     50,
  
  /* Loop starts here; it will be run five times */
  CMD_LOOP_BEGIN,  5,
  
  /* Red-green-blue-off for one second each */
  CMD_SET_COLOR, 255,   0,   0,   50,
  CMD_SET_COLOR,   0, 255,   0,   50,
  CMD_SET_COLOR,   0,   0, 255,   50,
  CMD_SET_COLOR,   0,   0,   0,   50,
  
  /* Red-green-blue-off for 0.5 seconds each */
  CMD_SET_COLOR, 255,   0,   0,   25,
  CMD_SET_COLOR,   0, 255,   0,   25,
  CMD_SET_COLOR,   0,   0, 255,   25,
  CMD_SET_COLOR,   0,   0,   0,   25,
  
  /* Loop ends here */
  CMD_LOOP_END,
  
  /* At this point we should be at 34 seconds.
   * Wait until we reach 40 seconds = 40000 msec.
   * 40000 = 10011100 01000000, which ends up being
   * 11000000 10111000 00000010 in varint encoding */
  CMD_WAIT_UNTIL, 192, 184, 2,
  
  /* Rapid flash at the end */
  CMD_LOOP_BEGIN, 16,
  CMD_SET_WHITE, 6,
  CMD_SET_BLACK, 6,
  CMD_LOOP_END,
  CMD_SET_WHITE, 100,
  CMD_SET_BLACK, 0,
  
  /* Program end marker */
  CMD_END
};

ConstantSRAMBytecodeStore bytecodeStore(bytecode);

