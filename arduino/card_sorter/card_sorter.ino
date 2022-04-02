// Copyright 2022 Kennet Belenky
//
// This file is part of OpenSorts.
//
// OpenSorts is free software: you can redistribute it and/or modify it under
// the terms of the GNU General Public License as published by the Free Software
// Foundation, either version 3 of the License, or (at your option) any later
// version.
//
// OpenSorts is distributed in the hope that it will be useful, but WITHOUT ANY
// WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
// A PARTICULAR PURPOSE. See the GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License along with
// OpenSorts. If not, see <https://www.gnu.org/licenses/>.

#include <AccelStepper.h>
#include <Adafruit_MotorShield.h>
#include <ArduinoJson.h>
#include <Wire.h>

Adafruit_MotorShield AFMS = Adafruit_MotorShield();

struct {
  struct {
    Adafruit_DCMotor *motor;
    uint8_t sensor;
    uint8_t direction;
    unsigned long flush_duration;
    unsigned long runout_duration;
    uint8_t primary_speed;
    uint8_t secondary_speed;
  } primary_hopper;
  struct {
    Adafruit_DCMotor *motor;
    uint8_t sensor;
    uint8_t direction;
    uint8_t feed_speed;
    uint8_t pullback_speed;
    unsigned long pullback_duration;
  } secondary_hopper;
  struct {
    Adafruit_DCMotor *motor;
    uint8_t direction;
    uint8_t return_sensor;
    uint8_t sensor1;
    uint8_t sensor2;
    uint8_t speed;
  } tray;
} device;

template <typename Direction, typename Component>
void StartMotor(const Component &component, Direction dir, uint8_t speed) {
  component.motor->run(dir(component.direction));
  component.motor->setSpeed(speed);
}

template <typename Component> void StopMotor(const Component &component) {
  component.motor->setSpeed(0);
}

bool IsCardInSecondaryHopper() {
  return !digitalRead(device.secondary_hopper.sensor);
}

bool IsCardInPrimaryHopper() {
  return !digitalRead(device.primary_hopper.sensor);
}

bool IsCardInTray() {
  return (!digitalRead(device.tray.sensor1)) ||
         (!digitalRead(device.tray.sensor2));
}

bool IsTrayMotorReturned() { return !digitalRead(device.tray.return_sensor); }

uint8_t Forward(uint8_t direction) {
  return direction == 0 ? FORWARD : BACKWARD;
}

uint8_t Backward(uint8_t direction) {
  return direction == 0 ? BACKWARD : FORWARD;
}

// State machine controlling the operation of the primary hopper.
class PrimaryHopperDriver {
public:
  enum State { PAUSED, READY, FEEDING, FLUSHING, RUNOUT, EMPTY };

  const char *StateName(State state) {
    switch (state) {
    case PAUSED:
      return "paused";
    case READY:
      return "ready";
    case FEEDING:
      return "feeding";
    case FLUSHING:
      return "flushing";
    case RUNOUT:
      return "runout";
    case EMPTY:
      return "empty";
    }
  }

  void Start() { state_ = READY; }

  State GetState() const { return state_; }

  void ProcessStep() {
    switch (state_) {
    case PAUSED:
      // Do nothing.
      break;

    case READY:
      // The secondary hopper has requested a card.
      if (IsCardInSecondaryHopper()) {
        // The secondary hopper has a card, so go back to paused.
        SetState(PAUSED);
      } else if (IsCardInPrimaryHopper()) {
        // There's a card in the primary hopper, so we start the feed motor.
        StartMotor();
        SetState(FEEDING);
      } else {
        // The sensor says there's no card in the primary hopper, but there
        // might still be one partially fed (and not blocking the sensor). Run
        // the motor for a little while just to make sure.
        flush_end_time_ = millis() + device.primary_hopper.flush_duration;
        StartFlush();
        SetState(FLUSHING);
      }
      break;

    case FLUSHING:
      // We stop flushing either when the secondary hopper receives a card, or
      // when enough time has passed that we're confident there are no more
      // cards.
      if (IsCardInSecondaryHopper()) {
        // The flush resulted in a card.
        runout_end_time_ = millis() + device.primary_hopper.runout_duration;
        StopPrimaryMotor();
        SetState(RUNOUT);
      } else if (millis() > flush_end_time_) {
        // No card came from the flush. The hopper is truly empty.
        StopPrimaryMotor();
        StopSecondaryMotor();
        SetState(EMPTY);
      }

    case FEEDING:
      // Keep feeding until the secondary hopper has a card.
      if (IsCardInSecondaryHopper()) {
        runout_end_time_ = millis() + device.primary_hopper.runout_duration;
        StopPrimaryMotor();
        SetState(RUNOUT);
      }
      break;

    case RUNOUT:
      // The card has been detected in the secondary hopper, but we keep running
      // the secondary hopper motor for just a moment longer in order to help
      // the card fully engage with the secondary hopper's feed wheels.
      if (millis() > runout_end_time_) {
        StopSecondaryMotor();
        SetState(PAUSED);
      }

    case EMPTY:
      // Terminal state until Reset is called.
      break;
    }
  }

  void Reset() { SetState(PAUSED); }

private:
  static void StartMotor() {
    // Note: Whenever we're feeding, we also run the secondary hopper motor at a
    // low speed. This does two things. First, it keeps the leading edge of the
    // card from forcefully banging against the secondary feed wheels, which
    // might damage its edge. Second, it helps the card fully load onto the
    // secondary feed wheels.
    ::StartMotor(device.primary_hopper, Forward,
                 device.primary_hopper.primary_speed);
    ::StartMotor(device.secondary_hopper, Forward,
                 device.primary_hopper.secondary_speed);
  }

  static void StartFlush() { StartMotor(); }

  static void StopPrimaryMotor() { StopMotor(device.primary_hopper); }

  static void StopSecondaryMotor() { StopMotor(device.secondary_hopper); }

  void SetState(State new_state) {
    char buffer[128];
    sprintf(buffer, "Primary Hopper: %s -> %s", StateName(state_),
            StateName(new_state));
    Serial.println(buffer);
    state_ = new_state;
  }

  State state_ = PAUSED;
  unsigned long flush_end_time_;
  unsigned long runout_end_time_;
};

// State machine controlling the operation of the secondary hopper.
class SecondaryHopperDriver {
public:
  enum State {
    READY_TO_FILL,
    READY_TO_FEED,
    WAITING_FOR_FILL,
    FEEDING,
    PULLBACK,
    EMPTY
  };

  const char *StateName(State state) {
    switch (state) {
    case READY_TO_FILL:
      return "ready_to_fill";
    case READY_TO_FEED:
      return "ready_to_feed";
    case WAITING_FOR_FILL:
      return "waiting_for_fill";
    case FEEDING:
      return "feeding";
    case PULLBACK:
      return "pullback";
    case EMPTY:
      return "empty";
    }
  }

  SecondaryHopperDriver(PrimaryHopperDriver *primary) : primary_(primary) {}

  void Start() { feed_requested_ = true; }

  bool IsRunning() const {
    if (state_ == READY_TO_FEED || state_ == EMPTY) {
      return false;
    } else {
      return true;
    }
  }

  bool IsEmpty() const { return state_ == EMPTY; }

  void ProcessStep() {
    switch (state_) {
    case READY_TO_FILL:
      // Determine if we can feed a new card yet.
      if (IsCardInSecondaryHopper()) {
        // There's a card in the secondary hopper. We're ready.
        SetState(READY_TO_FEED);
      } else if (primary_->GetState() == PrimaryHopperDriver::EMPTY) {
        // The primary hopper is empty, and there's no card in the secondary
        // hopper, so we must be terminally empty.
        SetState(EMPTY);
      } else {
        // Tell the primary hopper to feed a new card, and wait for it to
        // arrive.
        primary_->Start();
        SetState(WAITING_FOR_FILL);
      }

    case READY_TO_FEED:
      // A card is in the secondary hopper. We just have to wait for the
      // controller to request the next card.
      if (feed_requested_) {
        feed_requested_ = false;
        StartFeedMotor();
        SetState(FEEDING);
      }
      break;

    case WAITING_FOR_FILL:
      if (primary_->GetState() == PrimaryHopperDriver::PAUSED ||
          primary_->GetState() == PrimaryHopperDriver::EMPTY) {
        // The primary hopper has completed our fill request. Go back to
        // READY_TO_FILL to determine what the next move is.
        SetState(READY_TO_FILL);
      }
      break;

    case FEEDING:
      // If a card is in the tray, figure out what's next.
      if (IsCardInTray()) {
        StopMotor();
        Serial.println("done");
        if (IsCardInSecondaryHopper()) {
          // There's still a card in the secondary hopper, so there's nothing to
          // do.
          SetState(READY_TO_FILL);
        } else {
          // "Pullback" solves a problem that's introduced by the primary
          // hopper's "Runout" feature. If there were two cards in the secondary
          // hopper, there's a chance that the second card can be fed far enough
          // forward that it's not triggering the secondary hopper's sensor.
          // When that happens, it would trigger the primary hopper to feed the
          // next card. But, the primary hopper also runs the secondary hopper
          // motor, which would then prematurely feed the card that is already
          // in the secondary hopper.
          //
          // The solution is to pull the secondary hopper wheel back for a
          // moment. This will result in the second card re-triggering the
          // secondary hopper's sensor, and preventing the premature feed.
          StartPullback();
          pullback_end_time_ =
              millis() + device.secondary_hopper.pullback_duration;
          SetState(PULLBACK);
        }
      }
      break;

    case PULLBACK:
      // Exit pullback if either the secondary hopper sensor is triggered, or
      // enough time has passed.
      if (IsCardInSecondaryHopper() || (millis() > pullback_end_time_)) {
        StopMotor();
        SetState(READY_TO_FILL);
      }

    case EMPTY:
      break;
    }
  }

  // Used when the primary hopper is reloaded.
  void Reset() {
    SetState(READY_TO_FILL);
    feed_requested_ = false;
    primary_->Reset();
  }

private:
  static void StartFeedMotor() {
    StartMotor(device.secondary_hopper, Forward,
               device.secondary_hopper.feed_speed);
  }

  static void StartPullback() {
    StartMotor(device.secondary_hopper, Backward,
               device.secondary_hopper.pullback_speed);
  }

  static void StopMotor() { ::StopMotor(device.secondary_hopper); }

  void SetState(State new_state) {
    char buffer[128];
    sprintf(buffer, "Secondary Hopper: %s -> %s", StateName(state_),
            StateName(new_state));
    Serial.println(buffer);
    state_ = new_state;
  }

  State state_ = READY_TO_FILL;
  PrimaryHopperDriver *primary_;
  bool feed_requested_ = false;
  unsigned long pullback_end_time_;
};

class TrayDriver {
public:
  enum State { PAUSED, SENDING, STOPPING, EMPTY };

  void SendLeft() {
    state_ = SENDING;
    StartMotor(device.tray, Forward, device.tray.speed);
  }

  void SendRight() {
    state_ = SENDING;
    StartMotor(device.tray, Backward, device.tray.speed);
  }

  bool IsPaused() { return state_ == PAUSED; }

  void ProcessStep() {
    switch (state_) {
    case PAUSED:
      // Do nothing.
      break;

    case SENDING:
      if (!IsCardInTray()) {
        state_ = STOPPING;
      }
      break;

    case STOPPING:
      if (IsCardInTray()) {
        state_ = SENDING;
      } else if (IsTrayMotorReturned()) {
        StopMotor(device.tray);
        state_ = PAUSED;
        Serial.println("done");
      }
      break;

    case EMPTY:
      break;
    }
  }

private:
  State state_ = PAUSED;
};

// You can't really tell if the feed system is fully empty of cards while
// anything is in motion. So the query state machine will wait until the tray
// and the hopper are at rest before it answers the question.
class HopperQuery {
public:
  enum State {
    IDLE,
    WAITING,
  };

  HopperQuery(const SecondaryHopperDriver *hopper, const TrayDriver *tray)
      : hopper_(hopper), tray_(tray) {}

  void Query() { state_ = WAITING; }

  void ProcessStep() {
    switch (state_) {
    case IDLE:
      // Do nothing.
      break;

    case WAITING:
      if (tray_->IsPaused() && !hopper_->IsRunning()) {
        state_ = IDLE;
        Serial.println(hopper_->IsEmpty() ? "empty" : "not_empty");
      }
      break;
    }
  }

private:
  const SecondaryHopperDriver *hopper_;
  const TrayDriver *tray_;
  State state_ = IDLE;
};

void Initialize() {
  // Read the json config that follows the initialize command and put everything
  // in the right place.
  auto json_text = Serial.readStringUntil('\n');
  StaticJsonDocument<1024> doc;
  DeserializationError error = deserializeJson(doc, json_text.c_str());
  if (error) {
    Serial.print(F("deserializeJson() failed: "));
    Serial.println(error.f_str());
    return;
  }
  Serial.println(F("Deserialization succeeded."));

  const auto primary = doc[F("primary_hopper")];
  device.primary_hopper.motor = AFMS.getMotor(primary[F("motor")]);
  device.primary_hopper.sensor = primary[F("sensor")];
  pinMode(device.primary_hopper.sensor, INPUT_PULLUP);
  device.primary_hopper.direction =
      primary[F("direction")] == 0 ? FORWARD : BACKWARD;
  device.primary_hopper.flush_duration = primary[F("flush_duration")];
  device.primary_hopper.runout_duration = primary[F("runout_duration")];
  device.primary_hopper.primary_speed = primary[F("primary_speed")];
  device.primary_hopper.secondary_speed = primary[F("secondary_speed")];

  const auto secondary = doc[F("secondary_hopper")];
  device.secondary_hopper.motor = AFMS.getMotor(secondary[F("motor")]);
  device.secondary_hopper.sensor = secondary[F("sensor")];
  pinMode(device.secondary_hopper.sensor, INPUT_PULLUP);
  device.secondary_hopper.direction =
      secondary[F("direction")] == 0 ? FORWARD : BACKWARD;
  device.secondary_hopper.feed_speed = secondary[F("feed_speed")];
  device.secondary_hopper.pullback_speed = secondary[F("pullback_speed")];
  device.secondary_hopper.pullback_duration = secondary[F("pullback_duration")];

  const auto tray = doc[F("tray")];
  device.tray.motor = AFMS.getMotor(tray[F("motor")]);
  device.tray.return_sensor = tray[F("return_sensor")];
  pinMode(device.tray.return_sensor, INPUT_PULLUP);
  device.tray.sensor1 = tray[F("sensor1")];
  pinMode(device.tray.sensor1, INPUT_PULLUP);
  device.tray.sensor2 = tray[F("sensor2")];
  pinMode(device.tray.sensor2, INPUT_PULLUP);
  device.tray.direction = tray[F("direction")] == 0 ? FORWARD : BACKWARD;
  device.tray.speed = tray[F("speed")];

  Serial.println(F("Initialized:"));
  Serial.println(doc.memoryUsage());
}

void setup() {
  Serial.begin(9600);  // set up Serial library at 9600 bps
  if (!AFMS.begin()) { // create with the default frequency 1.6KHz
    Serial.println(F("Motor shield initialization failure."));
    while (1) {
    }
  }
  // The motor shield takes a moment to come online, even after begin() was
  // called.
  delay(500);
}

void loop() {
  static bool initialized = false;
  static bool started = false;
  static PrimaryHopperDriver primary_hopper;
  static SecondaryHopperDriver secondary_hopper(&primary_hopper);
  static TrayDriver tray;
  static HopperQuery query(&secondary_hopper, &tray);

  if (started) {
    primary_hopper.ProcessStep();
    secondary_hopper.ProcessStep();
    tray.ProcessStep();
    query.ProcessStep();
  }

  if (Serial.available()) {
    auto result = Serial.readStringUntil('\n');
    if (result == "send_right") {
      tray.SendRight();
    } else if (result == "send_left") {
      tray.SendLeft();
    } else if (result == "next_card") {
      secondary_hopper.Start();
    } else if (result == "is_hopper_empty") {
      query.Query();
    } else if (result == "reset_hopper") {
      secondary_hopper.Reset();
      Serial.println("done");
    } else if (result == "is_hopper_reloaded") {
      Serial.println(IsCardInPrimaryHopper() ? "not_empty" : "empty");
    } else if (result == "query_sensors") {
      char buffer[128];
      sprintf(buffer, "query: %d, %d, %d, %d, %d",
              digitalRead(device.primary_hopper.sensor),
              digitalRead(device.secondary_hopper.sensor),
              digitalRead(device.tray.return_sensor),
              digitalRead(device.tray.sensor1),
              digitalRead(device.tray.sensor2));
      Serial.println(buffer);
    } else if (result == "start") {
      if (initialized) {
        started = true;
      } else {
        Serial.println(F("You must call `initialize` before `start`."));
      }
      Serial.println(F("done"));
    } else if (result == "initialize") {
      Initialize();
      initialized = true;
      Serial.println(F("done"));
    } else if (result == "primary_motor" && initialized) {
      StartMotor(device.primary_hopper, Forward, 120);
      delay(1000);
      StopMotor(device.primary_hopper);
      Serial.println(F("done"));
    } else if (result == "secondary_motor" && initialized) {
      StartMotor(device.secondary_hopper, Forward, 120);
      delay(1000);
      StopMotor(device.secondary_hopper);
      Serial.println(F("done"));
    } else if (result == "tray_motor" && initialized) {
      StartMotor(device.tray, Forward, 120);
      delay(1000);
      while (!IsTrayMotorReturned()) {}
      StopMotor(device.tray);
      Serial.println(F("done"));
    }
  }
}
