  #include <Keypad.h>

  // ---------- KEYPAD SETUP ----------
  const byte ROWS = 4;
  const byte COLS = 4;

  char keys[ROWS][COLS] = {
    { '1', '2', '3', 'A' },
    { '4', '5', '6', 'B' },
    { '7', '8', '9', 'C' },
    { '*', '0', 'Y', 'N' }
  };
   
  byte rowPins[ROWS] = { 13, 12, 11, 10 };
  byte colPins[COLS] = { 9, 8, 7, 6 };
  bool readKeys = false, choice= false;
  bool promo = false;
  //A preset place to move all pieces to
  String preset = "h9";

  Keypad keypad = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);

  // ---------- VARIABLES ----------
  char cmd[5];
  int count = 0;
  String piReceive = "";
  String piCommand = "";

  // ---------- SETUP ----------
  void setup() {
    Serial.begin(9600);
    pinMode(13, OUTPUT);
  }

  // ---------- LOOP ----------
  void loop() {

    // ===== RECEIVE COMMAND FROM PI =====
    while (Serial.available()) {
      char c = Serial.read();

      if (c == '\n') {
        handlePiCommand(piReceive);
        piReceive = "";  // clear buffer
      } else {
        piReceive += c;
      }
    }
    if (readKeys) readKeypad();
    else if (choice) readKeypad();
    else if (promo) readKeypad();
  }
  
  char cmd2 = '\0';
  void readKeypad() {
    // ===== READ KEYPAD =====
    char key = keypad.getKey();

    if (key) {
      if (key >= '1' && key <= '9') {
        if (count % 2 == 0) {
          // Store this input as a character
          cmd[count] = 'A' + (key - '1');  
          cmd2 = 'A' + (key - '1');  
        } else {
          cmd[count] = key;
        }
        count++;
      }

      if (count == 4) {
        cmd[4] = '\0';  // null terminate
        count = 0;
      }

      if (key == 'A') {
        if(choice || promo){
          if(cmd2 == 'A')
            cmd2 = 'y';
          else 
            cmd2 = 'n';
          Serial.println("heypi "+String(cmd2));
        }
        else if(readKeys)
          Serial.println("heypi m" + String(cmd));
        readKeys = false;
        choice = false;
        promo = false;
        cmd[count] = '\0'; 
        count = 0;
      }
    }
  }
  void moveMotor(String target){
    for(int i=0;i<5;i++){
      digitalWrite(13, HIGH);
      delay(500);
      digitalWrite(13, LOW);
      delay(500);
    }
  }
  // ---------- COMMAND HANDLER ----------
  void handlePiCommand(String command) {
    command.trim();
    piCommand = "";
    int spaceIndex = command.indexOf(' ');
    if(spaceIndex!=-1){
      piCommand = command.substring(spaceIndex+1);
    }
    //Initial piCommand to confirm if arduino is working as well
    if (piCommand.equalsIgnoreCase("rEaDy")){
      Serial.println("heypi startgame");
    }
    //Pi asks for keypad input
    else if (piCommand.equalsIgnoreCase("gEt")) {
      readKeys = true;
    } 
    else if (piCommand.equalsIgnoreCase("choice")) {
      choice = true;
    } 
    else if(piCommand.startsWith("p")){
      promo = true;
    }
    else {
      Serial.println("UNKNOWN_CMD");
    }
  }
