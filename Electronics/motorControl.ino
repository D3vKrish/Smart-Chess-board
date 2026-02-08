#include <AccelStepper.h>
#include <Servo.h>
#include <Math.h>

//CNC shield pins
#define MOTOR_X_STEP_PIN 2
#define MOTOR_X_DIR_PIN 5
#define MOTOR_Y_STEP_PIN 3
#define MOTOR_Y_DIR_PIN 6
#define ENABLE_PIN 8
#define LIMIT_X 9
#define LIMIT_Y 10

const long halfsquare = 270;
const float maxSpeed = 75000.0;
const float acceleration = 75000.0;
volatile bool limitHit = false;
volatile unsigned long lastHit = 0;

//Constants for homing
const float homingSpeed = 12000.0;
#define TIMEOUT 30000
#define BACKOFF_X 540
#define BACKOFF_Y 810

Servo servo;
AccelStepper leftMotor(AccelStepper::DRIVER, MOTOR_X_STEP_PIN, MOTOR_X_DIR_PIN);
AccelStepper rightMotor(AccelStepper::DRIVER, MOTOR_Y_STEP_PIN, MOTOR_Y_DIR_PIN);

const int servo_on = 0;
const int servo_off = 90;

String piReceive = "";
String piCommand = "";

void setup() {
  Serial.begin(9600);
  pinMode(LIMIT_X, INPUT_PULLUP);
  pinMode(LIMIT_Y, INPUT_PULLUP);
  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, LOW);  // Active low
  attachInterrupt(digitalPinToInterrupt(LIMIT_X), stop, FALLING);
  attachInterrupt(digitalPinToInterrupt(LIMIT_Y), stop, FALLING);
  leftMotor.setMaxSpeed(maxSpeed);
  leftMotor.setAcceleration(acceleration);

  rightMotor.setMaxSpeed(maxSpeed);
  rightMotor.setAcceleration(acceleration);

  servo.attach(11);
  servo.write(servo_off);
}
void stop() {
  unsigned long now = millis();
  if (now - lastHit > 40) {  // debounce
    limitHit = true;
    lastHit = now;
  }
}

void home() {

  unsigned long start = millis();
  leftMotor.setSpeed(0);
  rightMotor.setSpeed(0);
  leftMotor.move(-50000);
  rightMotor.move(-50000);
  while (digitalRead(LIMIT_X) == LOW) {
    leftMotor.run();
    rightMotor.run();

    if (millis() - start > TIMEOUT) {
      Serial.println("X timeout");
      break;
    }
  }

  leftMotor.setSpeed(0);
  rightMotor.setSpeed(0);
  delay(200);

  // Backoff X
  detachInterrupt(digitalPinToInterrupt(LIMIT_X));
  moveRelative(BACKOFF_X, BACKOFF_X);
  attachInterrupt(digitalPinToInterrupt(LIMIT_X), stop, FALLING);

  start = millis();
  leftMotor.move(50000);
  rightMotor.move(-50000);
  while (digitalRead(LIMIT_Y) == HIGH) {
    leftMotor.run();
    rightMotor.run();

    if (millis() - start > TIMEOUT) {
      Serial.println("Y timeout");
      break;
    }
  }

  leftMotor.setSpeed(0);
  rightMotor.setSpeed(0);
  delay(200);

  // Backoff Y
  detachInterrupt(digitalPinToInterrupt(LIMIT_Y));
  moveRelative(-BACKOFF_Y, BACKOFF_Y);
  attachInterrupt(digitalPinToInterrupt(LIMIT_Y, stop, FALLING);

  leftMotor.setCurrentPosition(0);
  rightMotor.setCurrentPosition(0);

  leftMotor.setMaxSpeed(maxSpeed);
  rightMotor.setMaxSpeed(maxSpeed);
  leftMotor.setAcceleration(acceleration);
  rightMotor.setAcceleration(acceleration);
  Serial.println("Moving to center");
  movePiece(3, -4);
  Serial.println("Homing Complete");
}

// void runMotorsBlocking() {
//   while (leftMotor.distanceToGo() != 0 || rightMotor.distanceToGo() != 0) {
//     leftMotor.run();
//     rightMotor.run();
//   }
// }

void runMotorsBlocking() {
  while (leftMotor.distanceToGo() != 0 || rightMotor.distanceToGo() != 0) {

    if (limitHit) {
      leftMotor.stop();
      rightMotor.stop();

      while (leftMotor.isRunning() || rightMotor.isRunning()) {
        leftMotor.run();
        rightMotor.run();
      }

      limitHit = false;
      return;
    }

    leftMotor.run();
    rightMotor.run();
  }
}

void moveRelative(long l, long r) {
  leftMotor.move(l);
  rightMotor.move(r);

  while (leftMotor.distanceToGo() != 0 || rightMotor.distanceToGo() != 0) {

    if (limitHit) {
      leftMotor.stop();
      rightMotor.stop();

      while (leftMotor.isRunning() || rightMotor.isRunning()) {
        leftMotor.run();
        rightMotor.run();
      }

      limitHit = false;
      return;
    }

    leftMotor.run();
    rightMotor.run();
  }
}

// void moveRelative(long l, long r) {
//   leftMotor.move(l);
//   rightMotor.move(r);

//   while (leftMotor.distanceToGo() != 0 || rightMotor.distanceToGo() != 0) {
//     leftMotor.run();
//     rightMotor.run();
//   }
// }

void moveLeft(double n) {
  long steps = labs(n * halfsquare);
  leftMotor.move(-steps);
  rightMotor.move(-steps);
  runMotorsBlocking();
}

void moveRight(double n) {
  long steps = labs(n * halfsquare);
  leftMotor.move(steps);
  rightMotor.move(steps);
  runMotorsBlocking();
}

void moveUp(double n) {
  long steps = labs(n * halfsquare);
  leftMotor.move(steps);
  rightMotor.move(-steps);
  runMotorsBlocking();
}

void moveDown(double n) {
  long steps = labs(n * halfsquare);
  leftMotor.move(-steps);
  rightMotor.move(steps);
  runMotorsBlocking();
}

void movePiece(int x, int y) {

  if (x == 0 && y != 0) {
    moveLeft(1);
    if (y < 0)
      moveDown(-2 * y);
    else
      moveUp(2 * y);
    moveRight(1);
  }

  else if (y == 0 && x != 0) {
    moveUp(1);
    if (x < 0)
      moveLeft(-2 * x);
    else
      moveRight(2 * x);
    moveDown(1);
  }

  else if (x > 0 && y > 0) {
    moveUp(1);
    moveRight(1);
    moveRight(2 * (x - 1));
    moveUp(2 * (y - 1));
    moveUp(1);
    moveRight(1);
  }

  else if (x < 0 && y < 0) {
    moveDown(1);
    moveLeft(1);
    moveLeft(2 * (x + 1));
    moveDown(2 * (y + 1));
    moveDown(1);
    moveLeft(1);
  }

  else if (x < 0 && y > 0) {
    moveUp(1);
    moveLeft(1);
    moveLeft(2 * (x + 1));
    moveUp(2 * (y - 1));
    moveUp(1);
    moveLeft(1);
  }

  else if (x > 0 && y < 0) {
    moveDown(1);
    moveRight(1);
    moveRight(2 * (x - 1));
    moveDown(2 * (y + 1));
    moveDown(1);
    moveRight(1);
  }
}
void executeMove(String move) {

  //home to initial
  {  //me2e4d4
    Serial.println("Home to initial");
    int x = (int)(move[1] - move[5]);
    int y = (int)(move[2] - move[6]);
    movePiece(x, y);
    servo.write(servo_on);
    delay(1000);
  }
  //initial to dest
  {
    Serial.println("Initial to dest");
    int x = (int)(move[3] - move[1]);
    int y = (int)(move[4] - move[2]);
    movePiece(x, y);
    servo.write(servo_off);
    delay(500);
  }
}

void decideMoves(String move) {
  String end = "md4d4d4";
  if (move.startsWith("m") || move.startsWith("p")) {
    executeMove(move);
  }
  //cf3e5f6
  //me5a9f6
  //mf3e5a9
  else if (move.startsWith("c")) {
    end[0] = 'm';
    end[1] = move[3];
    end[2] = move[4];
    end[3] = 'a';
    end[4] = '9';
    end[5] = move[5];
    end[6] = move[6];
    end[7] = 0;
    move[0] = 'm';
    move[5] = 'a';
    move[6] = '9';
    move[7] = 0;
    executeMove(end);
    executeMove(move);
  }
  //Handling castling
  else if (move.startsWith("a")) {
    executeMove(move);
    String side = move.substring(3, 5);

    if (side.equalsIgnoreCase("g1")) end = "mh1f1g1";
    else if (side.equalsIgnoreCase("c1")) end = "ma1d1c1";
    else if (side.equalsIgnoreCase("g8")) end = "mh8f8g8";
    else if (side.equalsIgnoreCase("c8")) end = "ma8d8c8";
    executeMove(end);
  }
  Serial.println("heypi ok");
}

void handlePiCommand(String command) {
  command.trim();
  piCommand = "";
  int spaceIndex = command.indexOf(' ');
  if (spaceIndex != -1) {
    piCommand = command.substring(spaceIndex + 1);
  }
  //Initial piCommand to confirm if arduino is working as well
  if (piCommand.equalsIgnoreCase("rEaDy")) {
    home();
    Serial.println("heypi startgame");
    return;
  }
  //Pi asks for keypad input
  Serial.println(piCommand);
  decideMoves(piCommand);
}

void loop() {
  //Initial piCommand to confirm if arduino is working as well

  if (Serial.available() > 0) {
    while (Serial.available()) {
      char c = Serial.read();

      if (c == '\n') {
        handlePiCommand(piReceive);
        piReceive = ""; 
      } else {
        piReceive += c;
      }
    }
  }
}
