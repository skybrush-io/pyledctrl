/**
 * \file errors.h
 * Constants for handling errors during the execution of the bytecode.
 */

#ifndef ERRORS_H
#define ERRORS_H

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
  ERR_SUCCESS,                           /**< No error */
  ERR_INVALID_COMMAND_CODE,              /**< Invalid command code found */
  ERR_SEEKING_NOT_SUPPORTED,             /**< Seeking not supported by the bytecode store */
  NUMBER_OF_ERRORS
} command_executor_error_t;

#ifdef __cplusplus
}
#endif

#endif
