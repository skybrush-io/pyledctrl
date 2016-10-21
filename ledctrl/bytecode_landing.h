/**
 * \file bytecode_landing.h
 * \brief Bytecode sequence that can be triggered during landing. It assigns a different color to different
 *        groups of drones so the pilots can see which one belongs to which RC controller.
 */

static u8 bytecode_landing[] = {
  CMD_SET_COLOR, 255, 255, 255,
  CMD_END
};

ConstantSRAMBytecodeStore bytecodeStore_landing(bytecode_landing);

/**
 * Sets the color used by this light system when the landing phase is triggered.
 *
 * \param  red    the value of the red channel
 * \param  green  the value of the green channel
 * \param  blue   the value of the blue channel
 */
void setLandingColor(u8 red, u8 green, u8 blue) {
  bytecode_landing[1] = red;
  bytecode_landing[2] = green;
  bytecode_landing[3] = blue;
}
