/**
 * \file bytecode_rc.h
 * \brief Bytecode sequence that controls the color of the LED strip from a remote
 *        signal source, channels 1, 2 and 3.
 */
 
static const u8 bytecode_rc[] = {
  CMD_LOOP_BEGIN, 0,
  CMD_SET_COLOR_FROM_CHANNELS, 1, 2, 3, 0,
  CMD_LOOP_END,
  CMD_END
};

ConstantSRAMBytecodeStore bytecodeStore_rc(bytecode_rc);

