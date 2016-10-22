/**
 * \file bytecode_timing_test.h
 * \brief Timing test sequence for ledctrl
 */
 
static const u8 bytecode[] = {
  /* Loop starts here */
  CMD_LOOP_BEGIN,  0,
  
  /* Red-green-blue-off for one second each */
  CMD_SET_COLOR, 128,   0,   0,   50,
  CMD_SET_COLOR,   0, 128,   0,   50,
  CMD_SET_COLOR,   0,   0, 128,   50,
  CMD_SET_COLOR,   0,   0,   0,   50,
  
  /* Loop ends here */
  CMD_LOOP_END,
  
  /* Program end marker */
  CMD_END
};

ConstantSRAMBytecodeStore bytecodeStore(bytecode);

