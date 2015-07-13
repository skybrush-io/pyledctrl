#include <Arduino.h>
#include <math.h>
#include "config.h"

class VoltMeter {
//private:
public:
	int readedvalue;


	float mod_duty;
	float mod_duty_last;



	float measure()
	{
		readedvalue = analogRead(VOLTMETER_PIN);
		Serial.println("readedvalue:");
		Serial.println(readedvalue);
		mod_duty = (LIGHT_COEFF / ((float)readedvalue / 1023));
		if (mod_duty> 1) mod_duty = 1;
		if (mod_duty < 0) mod_duty = 0;
		if (abs(mod_duty - mod_duty_last) < 0.05)
			mod_duty = mod_duty_last;
		else
			mod_duty_last = mod_duty;
		return mod_duty;
	}
};
