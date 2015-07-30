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
  /* 0x02 = CMD_SLEEP
   * Arguments: duration
   */
  {
    .arg_count = 1
  },
  /* 0x03 = CMD_WAIT_UNTIL
   * Arguments: duration (varint)
   */
  {
    .arg_count = ARG_VARINT
  },
  /* 0x04 = CMD_SET_COLOR
   * Arguments: red, green, blue, duration
   */
  {
    .arg_count = 4
  },
  /* 0x05 = CMD_SET_GRAY
   * Arguments: gray, duration
   */
  {
    .arg_count = 2
  },
  /* 0x06 = CMD_SET_BLACK
   * Arguments: duration
   */
  {
    .arg_count = 1
  },
  /* 0x07 = CMD_SET_WHITE
   * Arguments: duration
   */
  {
    .arg_count = 1
  },
  /* 0x08 = CMD_FADE_TO_COLOR
   * Arguments: red, green, blue, duration, easing
   */
  {
    .arg_count = 5
  },
  /* 0x09 = CMD_FADE_TO_GRAY
   * Arguments: gray, duration, easing
   */
  {
    .arg_count = 3
  },
  /* 0x0A = CMD_FADE_TO_BLACK
   * Arguments: duration, easing
   */
  {
    .arg_count = 2
  },
  /* 0x0B = CMD_FADE_TO_WHITE
   * Arguments: duration, easing
   */
  {
    .arg_count = 2
  },
  /* 0x0C = CMD_LOOP_BEGIN
   * Arguments: counter
   */
  {
    .arg_count = 1
  },
  /* 0x0D = CMD_LOOP_END */
  {
    .arg_count = 0
  },
  /* 0x0E = CMD_RESET_TIMER */
  {
    .arg_count = 0
  },
  /* 0x0F = CMD_JUMP
   * Arguments: address (varint)
   */
  {
    .arg_count = ARG_VARINT
  },
  /* 0x10 = CMD_SET_COLOR_FROM_CHANNELS
   * Arguments: red channel, green channel, blue channel, duration
   */
  {
    .arg_count = 4
  },
  /* 0x11 = CMD_FADE_TO_COLOR_FROM_CHANNELS
   * Arguments: red channel, green channel, blue channel, duration, easing
   */
  {
    .arg_count = 5
  }
};
