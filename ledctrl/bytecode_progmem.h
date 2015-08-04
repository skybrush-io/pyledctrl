/**
 * \file bytecode_rc.h
 * \brief Test sequence that is stored in the PROGMEM area.
 */
#include <avr/pgmspace.h>

static const u8 bytecode[] PROGMEM = {
  CMD_SET_COLOR, 255, 255, 255, DURATION_BYTE(1),
  CMD_SET_COLOR, 0, 0, 0, DURATION_BYTE(1),
  /* Address 10 starts here */
  CMD_SET_COLOR, 255, 0, 0, DURATION_BYTE(2),
  CMD_SET_COLOR, 0, 255, 0, DURATION_BYTE(2),
  CMD_SET_COLOR, 0, 0, 255, DURATION_BYTE(2),
  CMD_SET_COLOR, 0, 0, 0, DURATION_BYTE(2),
  CMD_SET_COLOR, 255, 255, 255, DURATION_BYTE(2),
  CMD_JUMP, 10,
  CMD_END
};

PROGMEMBytecodeStore bytecodeStore(bytecode);

