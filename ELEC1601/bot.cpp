#include <Servo.h>                      // Include servo library

const int LirLedPin = 10, LirReceiverPin = 11;
const int LredLedPin = A2;

const int RirLedPin = 2, RirReceiverPin = 3;
const int RredLedPin = A0;

const int MirLedPin = 6, MirReceiverPin = 7;
const int MredLedPin = A1;

int Rsensor = A0;
int Lsensor = A1;

int Rvalue = 0;
int Lvalue = 0;
int Mvalue = 0;

Servo Lservo, Rservo;

void setup()
{
    delay(3000);
    Serial.begin(9600);
    Lservo.attach(13);     
    Rservo.attach(12);
}

void loop()
{
  /*
  Rvalue = RirDetect(38000);
  Lvalue = LirDetect(38000);
  Mvalue = MirDetect(38600); // try to detect a wall with distance <= 9cm
  //Opening on Right wall --> Right turn
  if (Rvalue == 1) {
    delay(500);
    Rturn90();
    Serial.println("turning right");
  }  
  //Opening on Left wall --> Left turn
  else if (Lvalue==1) {
    delay(500);
    Lturn90();
    Serial.println("turning left");
  }  
  else {
    Forward();
    Serial.println("move forward");
  }
  
  delay(100);
  */

  if (irDistance(1) != irDistance(2)){
    Backward();
  }
  else{
    Forward();
  }
}

void Rturn90()
{
  Rservo.writeMicroseconds(1495);
  Lservo.writeMicroseconds(1680);
  delay(900);
}

void Lturn90()
{
  Rservo.writeMicroseconds(1340);
  Lservo.writeMicroseconds(1490);
  delay(900);
}

void Forward()
{
  Rservo.writeMicroseconds(1340);
  Lservo.writeMicroseconds(1680);
  delay(100);
}

void Backward()
{
  Rservo.writeMicroseconds(1680);
  Lservo.writeMicroseconds(1340);
  delay(100);
}
/*
int LirDetect(long frequency)
{
  tone(LirLedPin, frequency);                 // Turn on the IR LED square wave
  delay(1);                                  // Wait 1 ms
  noTone(LirLedPin);                          // Turn off the IR LED
  int Lir = digitalRead(LirReceiverPin);       // IR receiver -> ir variable
  delay(1);                                  // Down time before recheck
  return Lir;                                 // Return 0 detect, 1 no detect
}

int RirDetect(long frequency)
{
  tone(RirLedPin, frequency);                 // Turn on the IR LED square wave
  delay(1);                                  // Wait 1 ms
  noTone(RirLedPin);                          // Turn off the IR LED
  int Rir = digitalRead(RirReceiverPin);       // IR receiver -> ir variable
  delay(1);                                  // Down time before recheck
  return Rir;                                 // Return 0 detect, 1 no detect
}

int MirDetect(long frequency)
{
  tone(MirLedPin, frequency);                 // Turn on the IR LED square wave
  delay(1);                                  // Wait 1 ms
  noTone(MirLedPin);                          // Turn off the IR LED
  int Mir = digitalRead(MirReceiverPin);       // IR receiver -> ir variable
  delay(1);                                  // Down time before recheck
  return Mir;                                 // Return 0 detect, 1 no detect
}
*/
int irDetect(int side, long frequency) // side = 0 -> mid, side = 1 -> left, side = 2 -> right
{
  if (side != 0 && side != 1 && side != 2){
    return -1;
  }
  int irLedPin = 0;
  int irReceiverPin = 0;
  if (side == 0){
    irLedPin = MirLedPin;
    irReceiverPin = MirReceiverPin;
  }
  else if (side == 1){
    irLedPin = LirLedPin;
    irReceiverPin = LirReceiverPin;
  }
  else{
    irLedPin = RirLedPin;
    irReceiverPin = RirReceiverPin;
  }
  tone(irLedPin, frequency);                 // Turn on the IR LED square wave
  delay(1);                                  // Wait 1 ms
  noTone(irLedPin);                          // Turn off the IR LED
  int ir = digitalRead(irReceiverPin);       // IR receiver -> ir variable
  delay(1);                                  // Down time before recheck
  return ir;                                 // Return 0 detect, 1 no detect
}

int irDistance(int side) // side = 0 -> mid, side = 1 -> left, side = 2 -> right
{
  if (side != 0 && side != 1 && side != 2){
    return -1;
  }
   int distance = 0;
   for(long f = 38000; f <= 42000; f += 100)
   {
      distance += irDetect(side, f);
   }
   return distance;
}
