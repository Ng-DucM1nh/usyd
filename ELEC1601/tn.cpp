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
  pinMode(LirReceiverPin, INPUT);
  pinMode(RirReceiverPin, INPUT);
  pinMode(MirReceiverPin, INPUT);
  pinMode(LirLedPin, OUTPUT);
  pinMode(RirLedPin, OUTPUT);
  pinMode(MirLedPin, OUTPUT);
  pinMode(LredLedPin, OUTPUT);
  pinMode(RredLedPin, OUTPUT);
  pinMode(MredLedPin, OUTPUT);
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

  int MDetect = irDetect(0, 38000);
  int LDetect = irDetect(1, 39400);
  int RDetect = irDetect(2, 42100);
  if (LDetect == 1 || RDetect == 1){
    // either left wall or right wall is really close
    int l = LDetect;
    int r = RDetect;
    if (r == 1 && l == 0){
      // right wall is really close
      Serial.println("right wall closer");
      Lturn(10);
    }
    else if (l == 1 && r == 0){
      // left wall is really close
      Serial.println("left wall closer");
      Rturn(10);
    }
  }
  else{
    Forward();
  }
  digitalWrite(LredLedPin, LOW);
  digitalWrite(RredLedPin, LOW);
  digitalWrite(MredLedPin, LOW);
}

// time = 900 -> turn 90 degree
void Rturn(int time)
{
  Rservo.writeMicroseconds(1495);
  Lservo.writeMicroseconds(1680);
  delay(time);
}

void Lturn(int time)
{
  Rservo.writeMicroseconds(1340);
  Lservo.writeMicroseconds(1490);
  delay(time);
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

int irDetect(int side, long frequency) // side = 0 -> mid, side = 1 -> left, side = 2 -> right
{
  if (side != 0 && side != 1 && side != 2){
    return -1;
  }
  int irLedPin = 0;
  int irReceiverPin = 0;
  int redLedPin = 0;
  if (side == 0){
    irLedPin = MirLedPin;
    irReceiverPin = MirReceiverPin;
    redLedPin = MredLedPin;
  }
  else if (side == 1){
    irLedPin = LirLedPin;
    irReceiverPin = LirReceiverPin;
    redLedPin = LredLedPin;
  }
  else{
    irLedPin = RirLedPin;
    irReceiverPin = RirReceiverPin;
    redLedPin = RredLedPin;
  }
  tone(irLedPin, frequency);                 // Turn on the IR LED square wave
  delay(1);                                  // Wait 1 ms
  noTone(irLedPin);                          // Turn off the IR LED
  int ir = digitalRead(irReceiverPin);       // IR receiver -> ir variable
  delay(1);                                  // Down time before recheck
  if (ir == 0){
    digitalWrite(redLedPin, HIGH);
  }
  return 1 - ir;                                 // Return 1 detect, 0 no detect
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
