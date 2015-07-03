#define __ASSERT_USE_STDERR

#include "config.h"
#include "commands.h"
#include "executor.h"
#include "led.h"
#include "led_strip.h"
#include "switch.h"

LED builtinLed;
LEDStrip ledStrip(RED_PWM_PIN, GREEN_PWM_PIN, BLUE_PWM_PIN);
Switch mainSwitch(MAIN_SWITCH_PIN);

CommandExecutor executor(&ledStrip, &builtinLed);

static const u8 bytecode[] = {
  /* White-off-white-off for one second each */
  CMD_SET_GRAY,  255, DURATION_BYTE(1),
  CMD_SET_GRAY,    0, DURATION_BYTE(1),
  CMD_SET_WHITE, DURATION_BYTE(1),
  CMD_SET_BLACK, DURATION_BYTE(0),
  CMD_SLEEP,     DURATION_BYTE(1),

  /* Loop starts here; it will be run five times */
  CMD_LOOP_BEGIN,  5,
  
  /* Red-green-blue-off for one second each */
  CMD_SET_COLOR, 255,   0,   0,   DURATION_BYTE(1),
  CMD_SET_COLOR,   0, 255,   0,   DURATION_BYTE(1),
  CMD_SET_COLOR,   0,   0, 255,   DURATION_BYTE(1),
  CMD_SET_COLOR,   0,   0,   0,   DURATION_BYTE(1),
  
  /* Red-green-blue-off for 0.5 seconds each */
  CMD_SET_COLOR, 255,   0,   0,   DURATION_BYTE(0.5),
  CMD_SET_COLOR,   0, 255,   0,   DURATION_BYTE(0.5),
  CMD_SET_COLOR,   0,   0, 255,   DURATION_BYTE(0.5),
  CMD_SET_COLOR,   0,   0,   0,   DURATION_BYTE(0.5),

  /* Loop ends here */
  CMD_LOOP_END,

  /* At this point we should be at 34 seconds.
   * Wait until we reach 40 seconds = 40000 msec.
   * 40000 = 10011100 01000000, which ends up being
   * 11000000 10111000 00000010 in varint encoding */
  CMD_WAIT_UNTIL, 192, 184, 2,

  /* Rapid flash at the end */
  CMD_LOOP_BEGIN, 16,
  CMD_SET_WHITE, DURATION_BYTE(0.125),
  CMD_SET_BLACK, DURATION_BYTE(0.125),
  CMD_LOOP_END,
  CMD_SET_WHITE, DURATION_BYTE(2),
  CMD_SET_BLACK,
  
  /* Program end marker */
  CMD_END
};

void setup() {
  // Configure the serial port where we will listen for commands
  Serial.begin(SERIAL_BAUD_RATE);

  // Load the bytecode into the executor
  executor.load(bytecode);
}

void loop() {
  // Check the main switch
  if (!mainSwitch.on()) {
    // Turn off the LEDs
    builtinLed.off();
    ledStrip.off();
    return;
  }

  // Make a step with the executor
  executor.step();
}

/**
 * \brief Forwards assertion error messages to the serial link.
 */
void __assert(const char *__func, const char *__file, int __lineno, const char *__sexp) {
    Serial.println(__func);
    Serial.println(__file);
    Serial.println(__lineno, DEC);
    Serial.println(__sexp);
    Serial.flush();
    abort();
}
