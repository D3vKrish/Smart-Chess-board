#include <AccelStepper.h>
#include <Servo.h>

//CNC shield pins
#define MOTOR_X_STEP_PIN 2
#define MOTOR_X_DIR_PIN  5
#define MOTOR_Y_STEP_PIN 3
#define MOTOR_Y_DIR_PIN  6
#define ENABLE_PIN       8  

const long halfsquare = 270; 
const float maxSpeed = 75000.0;   
const float acceleration = 75000.0; 

Servo servo;
AccelStepper leftMotor(AccelStepper::DRIVER, MOTOR_X_STEP_PIN, MOTOR_X_DIR_PIN);
AccelStepper rightMotor(AccelStepper::DRIVER, MOTOR_Y_STEP_PIN, MOTOR_Y_DIR_PIN);

const int servo_on = 0;
const int servo_off = 90;

String piReceive = "";
String piCommand = "";

void setup() {
  Serial.begin(9600);

  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, LOW); // Active low

  leftMotor.setMaxSpeed(maxSpeed);
  leftMotor.setAcceleration(acceleration);
  
  rightMotor.setMaxSpeed(maxSpeed);
  rightMotor.setAcceleration(acceleration);

  servo.attach(11);
  servo.write(servo_off);
}

void runMotorsBlocking() {
  while (leftMotor.distanceToGo() != 0 || rightMotor.distanceToGo() != 0) {
    leftMotor.run();
    rightMotor.run();
  }
}

void moveLeft(double n) {
  long steps = n * halfsquare;
  leftMotor.move(-steps);
  rightMotor.move(-steps);
  runMotorsBlocking();
}

void moveRight(double n) {
  long steps = n * halfsquare;
  leftMotor.move(steps);
  rightMotor.move(steps);
  runMotorsBlocking();
}

void moveUp(double n) {
  long steps = n * halfsquare;
  leftMotor.move(steps);
  rightMotor.move(-steps);
  runMotorsBlocking();
}

void moveDown(double n) {
  long steps = n * halfsquare;
  leftMotor.move(-steps);
  rightMotor.move(steps);
  runMotorsBlocking();
}


void loop() {
  if (Serial.available()) {
        String command = Serial.readStringUntil('\n'); 
        command.trim();
        if (command == "w") {
            moveUp(1); 
        } 
        else if (command == "s") {
            moveDown(1); 
        } 
        else if (command == "a") {
            moveLeft(1); 
        } 
        else if (command == "d") {
            moveRight(1); 
        } 
  }
}
