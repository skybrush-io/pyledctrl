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

// Set the following macro to the number of the test sequence that you want to start
// 0 = simple test sequence
// 1 = testing transition types and easing functions
#define BYTECODE_INDEX 1

static const u8 bytecode[] = {
#if BYTECODE_INDEX == 0
#  include "bytecode_first_test.h"
#elif BYTECODE_INDEX == 1
#  include "bytecode_transition_test.h"
#endif
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
