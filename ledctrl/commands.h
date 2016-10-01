/**
 * \file commands.h
 * \brief Commands and command queue for the LED controller project.
 */

#ifndef COMMANDS_H
#define COMMANDS_H

#include <Arduino.h>
#include "types.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Enum containing codes for the different commands in the low-level
 * bytecode of the LED strip program.
 */
typedef enum {
  CMD_END,                         /**< 0x00 = End of program */
  CMD_NOP,                         /**< 0x01 = No operation */
  CMD_SLEEP,                       /**< 0x02 = Sleep */
  CMD_WAIT_UNTIL,                  /**< 0x03 = Wait until */
  CMD_SET_COLOR,                   /**< 0x04 = Set color */
  CMD_SET_GRAY,                    /**< 0x05 = Set grayscale color */
  CMD_SET_BLACK,                   /**< 0x06 = Set color to black */
  CMD_SET_WHITE,                   /**< 0x07 = Set color to white */
  CMD_FADE_TO_COLOR,               /**< 0x08 = Fade to color */
  CMD_FADE_TO_GRAY,                /**< 0x09 = Fade to grayscale color */
  CMD_FADE_TO_BLACK,               /**< 0x0A = Fade to black */
  CMD_FADE_TO_WHITE,               /**< 0x0B = Fade to white */
  CMD_LOOP_BEGIN,                  /**< 0x0C = Mark the beginning of a loop */
  CMD_LOOP_END,                    /**< 0x0D = Mark the end of a loop */
  CMD_RESET_CLOCK,                 /**< 0x0E = Reset the internal clock */
  CMD_UNUSED_1,
  CMD_SET_COLOR_FROM_CHANNELS,     /**< 0x10 = Set color from channels */
  CMD_FADE_TO_COLOR_FROM_CHANNELS, /**< 0x11 = Fade to color from channels */
  CMD_JUMP,                        /**< 0x12 = Jump to address */
  CMD_TRIGGERED_JUMP,              /**< 0x13 = Triggered jump to address */
  NUMBER_OF_COMMANDS,
} command_t;

/**
 * Structure that defines the extra information we provide about each
 * command such as the number of arguments that we expect for the
 * command.
 */
typedef struct {
  u8 arg_count;
  u8 flags;
} command_info_t;

/**
 * Special constant that is used in the \c arg_count member of
 * \c command_info_t to denote a command that uses a given number of arguments,
 * the last of which is variable-length.
 */
#define LAST_ARG_IS_VARINT(x) ((x) + 127)

/**
 * Array that holds information for each of the commands that we support.
 */
extern const command_info_t COMMAND_INFO[NUMBER_OF_COMMANDS];

#ifdef __cplusplus
}
#endif

#endif


