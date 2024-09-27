int find_freq_for(int x)
{
    int ans = -1;
    int current_freq = 38000;
    while (current_freq <= 46000){
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
