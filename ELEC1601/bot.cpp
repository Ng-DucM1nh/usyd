#include <Servo.h>  // Include servo library

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

int dem = 0;

Servo Lservo, Rservo;

void setup() {
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

void loop() {

  Rvalue = irDetect(2, 38094);
  Lvalue = irDetect(1, 37600);
  Mvalue = irDetect(0, 39583);  // try to detect a wall with distance <= 9cm
  if (Mvalue == 1 && Rvalue == 1 && Lvalue == 1) {
    Backward(1350);
    Rturn(4600);
  }
  if (Mvalue == 1) {
    // front wall
    Serial.println("front wall");
    if (Rvalue == 0) {
      //Opening on Right wall --> Right turn
      preRturn(600);
      Rturn(110);
      Serial.println("turning right");
    } else if (Lvalue == 0) {
      //Opening on Left wall --> Left turn
      preLturn(600);
      Lturn(110);
      Serial.println("turning left");
    } else {
      Stop();
    }
  } else {
    Forward();
    Serial.println("move forward");
  }

  digitalWrite(LredLedPin, LOW);
  digitalWrite(RredLedPin, LOW);
  digitalWrite(MredLedPin, LOW);


  int LDetect = irDetect(1, 39995);
  int RDetect = irDetect(2, 41522);
  if (LDetect == 1 || RDetect == 1) {
    int l = LDetect;
    int r = RDetect;
    if (r == 1 && l == 0) {
      // right wall is closer
      Serial.println("right wall closer");
      Lturn(30);
    } else if (l == 1 && r == 0) {
      // left wall is closer
      Serial.println("left wall closer");
      Rturn(30);
    }
  }

  digitalWrite(LredLedPin, LOW);
  digitalWrite(RredLedPin, LOW);
  digitalWrite(MredLedPin, LOW);

  if (dem == 10){
    Forward();
    delay(1850);
    while (1) Stop();
  }
}

void Rturn(int time) {
  Rservo.writeMicroseconds(1680);
  Lservo.writeMicroseconds(1680);
  delay(time);
}

void Lturn(int time) {
  Rservo.writeMicroseconds(1340);
  Lservo.writeMicroseconds(1340);
  delay(time);
}

void preRturn(int time) {
  Rservo.writeMicroseconds(1495);
  Lservo.writeMicroseconds(1680);
  delay(time);
}

void preLturn(int time) {
  Rservo.writeMicroseconds(1370);
  Lservo.writeMicroseconds(1490);
  delay(time);
  dem++;
}

void Forward() {
  Rservo.writeMicroseconds(1340);
  Lservo.writeMicroseconds(1680);
  delay(100);
}

void Backward(int time) {
  Rservo.writeMicroseconds(1680);
  Lservo.writeMicroseconds(1340);
  delay(time);
}

void Stop() {
  Rservo.writeMicroseconds(1495);
  Lservo.writeMicroseconds(1490);
}

int irDetect(int side, long frequency)  // side = 0 -> mid, side = 1 -> left, side = 2 -> right
{
  if (side != 0 && side != 1 && side != 2) {
    return -1;
  }
  int irLedPin = 0;
  int irReceiverPin = 0;
  int redLedPin = 0;
  if (side == 0) {
    irLedPin = MirLedPin;
    irReceiverPin = MirReceiverPin;
    redLedPin = MredLedPin;
  } else if (side == 1) {
    irLedPin = LirLedPin;
    irReceiverPin = LirReceiverPin;
    redLedPin = LredLedPin;
  } else {
    irLedPin = RirLedPin;
    irReceiverPin = RirReceiverPin;
    redLedPin = RredLedPin;
  }
  tone(irLedPin, frequency);            // Turn on the IR LED square wave
  delay(1);                             // Wait 1 ms
  noTone(irLedPin);                     // Turn off the IR LED
  int ir = digitalRead(irReceiverPin);  // IR receiver -> ir variable
  delay(1);                             // Down time before recheck
  if (ir == 0) {
    digitalWrite(redLedPin, HIGH);
  }
  return 1 - ir;  // Return 1 detect, 0 no detect
}

int irDistance(int side)  // side = 0 -> mid, side = 1 -> left, side = 2 -> right
{
  if (side != 0 && side != 1 && side != 2) {
    return -1;
  }
  int distance = 0;
  for (long f = 38000; f <= 42000; f += 100) {
    distance += irDetect(side, f);
  }
  return distance;
}
