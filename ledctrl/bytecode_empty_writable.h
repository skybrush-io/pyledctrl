/**
 * \file bytecode_empty_writable.h
 * \brief Empty writable bytecode store for ledctrl
 */

/**
 * \def MAX_BYTECODE_SIZE
 * Maximum allowed size of the bytecode store.
 */
#define MAX_BYTECODE_SIZE 1024

u8 bytecode[MAX_BYTECODE_SIZE] = {
  CMD_END
};

SRAMBytecodeStore bytecodeStore(bytecode, MAX_BYTECODE_SIZE);

