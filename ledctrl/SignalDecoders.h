#define NUMBEROFEDGES 9
#define PACKETSIZE 22000


#if PPM_INTERRUPT
/**
* PPM decoder header
*/
typedef struct
{
	volatile long current;
	volatile long last;
	volatile long period;
	volatile long Periods[NUMBEROFEDGES];
	volatile long fullperiod;
	volatile long fullperiod_begin;
	volatile long fullperiod_lastbegin;
} PPMtime;
volatile int CurrentChannel = 0;
int ReadedChannel;
long time_readed;

void ppmIT();
volatile void PPMsignalToSerial();
PPMtime ppmtime;


void ppmIT()
{

	ppmtime.current = micros();
	CurrentChannel++;
	ppmtime.period = ppmtime.current - ppmtime.last;
	if (CurrentChannel >= NUMBEROFEDGES | ppmtime.period >= PACKETSIZE / 3)
	{
		CurrentChannel = -1;

		ppmtime.fullperiod_begin = ppmtime.current;
		ppmtime.fullperiod = ppmtime.fullperiod_begin - ppmtime.fullperiod_lastbegin;
		ppmtime.fullperiod_lastbegin = ppmtime.current;
	}
	else
	{
		ppmtime.Periods[CurrentChannel] = ppmtime.period;
	}
	ppmtime.last = ppmtime.current;
}

/* function for senging signal values to serial port*/
volatile void PPMsignalToSerial()
{
	for (int i = 0; i <= NUMBEROFEDGES - 1; i++)
	{
		Serial.print(" ch: ");
		Serial.print(i);
		Serial.print(" : ");
		Serial.print(ppmtime.Periods[i]);
	}
	Serial.println();
	Serial.println(ppmtime.fullperiod);

}

#endif
#if PWM_INTERRUPT

/*
* PWM decoder header
*/

typedef struct
{
	volatile long current;
	volatile long last;
	volatile long period;
	volatile long period_begin;
	volatile long high;
	volatile long low;
} PWMtime;

PWMtime pwmtime;

/*
* Functions of PWM signal's interrupt
*/

void pwmIT()
{
	pwmtime.current = micros();
	if (bitRead(PIND, ITPIN) == HIGH)
	{
		pwmtime.period = pwmtime.current - pwmtime.period_begin;
		pwmtime.period_begin = pwmtime.current;

		pwmtime.high = pwmtime.current - pwmtime.last;
	}
	else
	{
		pwmtime.low = pwmtime.current - pwmtime.last;
	}
	pwmtime.last = pwmtime.current;
}

/* function for senging signal values to serial port*/
volatile void PWMsignalToSerial()
{
	Serial.println();
	Serial.print("high: ");
	Serial.print(pwmtime.high);
	Serial.print("  low: ");
	Serial.print(pwmtime.low);
	if (abs(pwmtime.period - pwmtime.high - pwmtime.low)<50)
		Serial.print("  [ok] ");
	else
		Serial.print("  [not ok]");
}

#endif