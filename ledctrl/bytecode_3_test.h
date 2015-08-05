/**
 * \file bytecode_3_test.h
 * \brief Another simple test sequence for ledctrl
 */
 
static const u8 bytecode[] = {
  CMD_SET_COLOR, 255, 255, 255, 50,
  CMD_SET_COLOR, 0, 0, 0, 50,
  /* Address 10 starts here */
  CMD_SET_COLOR, 255, 0, 0, 100,
  CMD_SET_COLOR, 0, 255, 0, 100,
  CMD_SET_COLOR, 0, 0, 255, 100,
  CMD_SET_COLOR, 0, 0, 0, 100,
  CMD_SET_COLOR, 255, 255, 255, 100,
  CMD_JUMP, 10,
  CMD_END
};

ConstantSRAMBytecodeStore bytecodeStore(bytecode);

