/**
 * \file commands.h
 * \brief Commands and command queue for the LED controller project.
 */

#ifndef COMMANDS_H
#define COMMANDS_H

#include <Arduino.h>

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
  CMD_JUMP,                        /**< 0x0F = Jump to address */
  CMD_SET_COLOR_FROM_CHANNELS,     /**< 0x10 = Set color from channels */
  CMD_FADE_TO_COLOR_FROM_CHANNELS, /**< 0x11 = Fade to color from channels */
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
 * \c command_info_t to denote a command that uses a single variable-length
 * int as its argument.
 */
#define ARG_VARINT 255

/**
 * Array that holds information for each of the commands that we support.
 */
extern const command_info_t COMMAND_INFO[NUMBER_OF_COMMANDS];

/**
 * Macro that encodes the given duration value into the short one-byte
 * format used in some commands.
 */
#define DURATION_BYTE(duration) (              \
    ((duration) >= 1) ? (                      \
        ((duration) < 192) ?                   \
            (u8)round(duration) :              \
            0                                  \
        ) :                                    \
        ((u8)((duration)*25) & 0x3F) | 0xC0    \
    )

#ifdef __cplusplus
}
#endif

#endif


