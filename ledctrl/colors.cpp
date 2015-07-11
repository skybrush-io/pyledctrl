#include <Arduino.h>
#include "colors.h"
#include "config.h"

const rgb_color_t COLOR_BLACK = { 0, 0, 0 };
const rgb_color_t COLOR_WHITE = { 255, 255, 255 };

rgb_color_t rgb_color_linear_interpolation(rgb_color_t first, rgb_color_t second, float ratio) {
  rgb_color_t result;

  result.red = constrain(first.red + (second.red - first.red) * ratio, 0, 255);
  result.green = constrain(first.green + (second.green - first.green) * ratio, 0, 255);
  result.blue = constrain(first.blue + (second.blue - first.blue) * ratio, 0, 255);

  return result;
}

