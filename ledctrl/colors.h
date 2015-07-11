/**
 * \file colors.h
 * \brief Color handling
 */

#ifndef COLORS_H
#define COLORS_H

#ifdef __cplusplus
extern "C" {
#endif

#include "types.h"

/**
 * Typedef for an RGB color.
 */
typedef struct {
  u8 red;           /**< The red component of the color */
  u8 green;         /**< The green component of the color */
  u8 blue;          /**< The blue component of the color */
} rgb_color_t;

/**
 * Constant for the black color.
 */
extern const rgb_color_t COLOR_BLACK;

/**
 * Constant for the white color.
 */
extern const rgb_color_t COLOR_WHITE;

/**
 * \brief Linearly interpolates between two colors
 * 
 * \param  first   the first color
 * \param  second  the second color
 * \param  ratio   the interpolation ratio; zero means the first color, 1 means
 *                 the second color. Values less than zero or greater than 1
 *                 are allowed.
 * \return the interpolated color
 */
rgb_color_t rgb_color_linear_interpolation(rgb_color_t first, rgb_color_t second, float ratio);

#ifdef __cplusplus
}
#endif

#endif
