const int irLedPin = 10, irReceiverPin = 11;
const int redLedPin = A2;

void setup()
{   
  pinMode(irReceiverPin, INPUT);            // IR receiver pin is an input
  pinMode(irLedPin, OUTPUT);                // IR LED pin is an ouput
  pinMode(redLedPin, OUTPUT);               
  Serial.begin(9600);
  Serial.println(find_freq_for(5));
}

void loop()
{
  
}

long find_freq_for(int distance)
{
  long ans = -1;
  long current_freq = 38000;
  Serial.println("initial frequency: ");
  Serial.println(current_freq);
  while (current_freq <= 46000){
    Serial.println("considering frequency :");
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
  return ans;
}
