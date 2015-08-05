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
   * Arguments: duration (varint)
   */
  {
    .arg_count = LAST_ARG_IS_VARINT(1)
  },
  /* 0x03 = CMD_WAIT_UNTIL
   * Arguments: timestamp (varint)
   */
  {
    .arg_count = LAST_ARG_IS_VARINT(1)
  },
  /* 0x04 = CMD_SET_COLOR
   * Arguments: red, green, blue, duration (varint)
   */
  {
    .arg_count = LAST_ARG_IS_VARINT(4)
  },
  /* 0x05 = CMD_SET_GRAY
   * Arguments: gray, duration (varint)
   */
  {
    .arg_count = LAST_ARG_IS_VARINT(2)
  },
  /* 0x06 = CMD_SET_BLACK
   * Arguments: duration (varint)
   */
  {
    .arg_count = LAST_ARG_IS_VARINT(1)
  },
  /* 0x07 = CMD_SET_WHITE
   * Arguments: duration (varint)
   */
  {
    .arg_count = LAST_ARG_IS_VARINT(1)
  },
  /* 0x08 = CMD_FADE_TO_COLOR
   * Arguments: red, green, blue, duration (varint)
   */
  {
    .arg_count = LAST_ARG_IS_VARINT(4)
  },
  /* 0x09 = CMD_FADE_TO_GRAY
   * Arguments: gray, duration (varint)
   */
  {
    .arg_count = LAST_ARG_IS_VARINT(2)
  },
  /* 0x0A = CMD_FADE_TO_BLACK
   * Arguments: duration
   */
  {
    .arg_count = LAST_ARG_IS_VARINT(1)
  },
  /* 0x0B = CMD_FADE_TO_WHITE
   * Arguments: duration
   */
  {
    .arg_count = LAST_ARG_IS_VARINT(1)
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
  /* 0x0F is unused */
  {
    .arg_count = 0
  },
  /* 0x10 = CMD_SET_COLOR_FROM_CHANNELS
   * Arguments: red channel, green channel, blue channel, duration (varint)
   */
  {
    .arg_count = LAST_ARG_IS_VARINT(4)
  },
  /* 0x11 = CMD_FADE_TO_COLOR_FROM_CHANNELS
   * Arguments: red channel, green channel, blue channel, duration (varint)
   */
  {
    .arg_count = LAST_ARG_IS_VARINT(4)
  },
  /* 0x12 = CMD_JUMP
   * Arguments: address (varint)
   */
  {
    .arg_count = LAST_ARG_IS_VARINT(1)
  },
  /* 0x13 = CMD_TRIGGERED_JUMP
   * Arguments: trigger parameters, address (varint)
   * 
   * Trigger parameters are encoded in a byte as follows:
   * 
   * xSRFCCCC
   * 
   * where CCCC is the index of the channel,
   * S is set to 1 if the trigger is one-shot and 0 if it is permanent,
   * R is set to 1 if the trigger should respond to the rising edge,
   * F is set to 1 if the trigger should respond to the falling edge.
   * Triggers can be cleared by setting both R and F to 0.
   */
  {
    .arg_count = LAST_ARG_IS_VARINT(2)
  },
};
