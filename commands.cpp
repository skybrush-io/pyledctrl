#include "commands.h"

const command_info_t COMMAND_INFO[NUMBER_OF_COMMANDS] = {
  /* 0x00 = CMD_END */
  {
    .arg_count = 0
  },
  /* 0x01 = CMD_NOP */
  {
    .arg_count = 0
  },
  /* 0x02 = CMD_SET_COLOR
   * Arguments: red, green, blue, duration
   */
  {
    .arg_count = 4
  },
  /* 0x03 = CMD_SET_GRAY
   * Arguments: gray, duration
   */
  {
    .arg_count = 2
  },
  /* 0x04 = CMD_SET_BLACK
   * Arguments: duration
   */
  {
    .arg_count = 1
  },
  /* 0x05 = CMD_SET_WHITE
   * Arguments: duration
   */
  {
    .arg_count = 1
  },
  /* 0x06 = CMD_SLEEP
   * Arguments: duration
   */
  {
    .arg_count = 1
  },
  /* 0x07 = CMD_WAIT_UNTIL
   * Arguments: duration (varint)
   */
  {
    .arg_count = ARG_VARINT
  },
  /* 0x08 = CMD_LOOP_BEGIN
   * Arguments: counter
   */
  {
    .arg_count = 1
  },
  /* 0x09 = CMD_LOOP_END */
  {
    .arg_count = 0
  },
  /* 0x0A = CMD_RESET_TIMER */
  {
    .arg_count = 0
  }
};
