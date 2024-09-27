const int irLedPin=6, irReceiverPin=7;
const int redLedPin = A1;

void setup()
{
  delay(3000);
  Serial.begin(9600);
  Serial.println(find_freq_for(8));
}

void loop()
{
}

int find_freq_for(int x)
{
  int ans = -1;
  long current_freq = 38000;
  while (current_freq <= 46000){
    Serial.println(current_freq);
    tone(irLedPin, current_freq);
    delay(1);
  noTone(irLedPin);
  int ir = digitalRead(irReceiverPin);
  if (ir == 0){
  // wall detected
  ans = current_freq;
  current_freq += 100;
  }
  else{
  // no wall detected
  break;
  }
  }
}
