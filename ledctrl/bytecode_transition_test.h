/**
 * \file bytecode_transition_test.h
 * \brief Test sequence for the transitions in ledctrl
 */

static const u8 bytecode[] = {
  CMD_LOOP_BEGIN, 0,
  
  CMD_FADE_TO_COLOR, 255,   0,   0, 50,
  CMD_FADE_TO_COLOR, 255, 255,   0, 50,
  CMD_FADE_TO_COLOR,   0, 255,   0, 50,
  CMD_FADE_TO_COLOR,   0, 255, 255, 50,
  CMD_FADE_TO_COLOR,   0,   0, 255, 50,
  CMD_FADE_TO_BLACK,                50,
  CMD_SLEEP, 100,
  
  CMD_LOOP_END,
  
  CMD_END
};

ConstantSRAMBytecodeStore bytecodeStore(bytecode);

