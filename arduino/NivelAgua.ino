#include <Arduino.h>

#if defined(ARDUINO_ARCH_ESP32)
constexpr uint8_t TRIG = 18;
constexpr uint8_t ECHO = 19;  // Usar divisor de tension con HC-SR04 de 5 V.
#else
constexpr uint8_t TRIG = 9;
constexpr uint8_t ECHO = 10;  // Conexion directa solo si la placa usa logica de 5 V (ej. Uno R3).
#endif

// Opcional: reemplaza estos ceros por las distancias calibradas para no repetir V y L.
float vacio = 0.0f;
float lleno = 0.0f;

float medirCm() {
  float muestras[7];
  uint8_t n = 0;
  for (uint8_t i = 0; i < 7; i++) {
    digitalWrite(TRIG, LOW);
    delayMicroseconds(3);
    digitalWrite(TRIG, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG, LOW);
    const unsigned long eco = pulseIn(ECHO, HIGH, 30000UL);
    const float cm = eco * 0.01715f;
    if (cm >= 2.0f && cm <= 400.0f) muestras[n++] = cm;
    delay(65);
  }
  if (n < 5) return -1.0f;
  for (uint8_t i = 1; i < n; i++) {
    const float valor = muestras[i];
    uint8_t j = i;
    while (j > 0 && muestras[j - 1] > valor) {
      muestras[j] = muestras[j - 1];
      j--;
    }
    muestras[j] = valor;
  }
  if (n % 2 == 0) return (muestras[n / 2 - 1] + muestras[n / 2]) / 2.0f;
  return muestras[n / 2];
}

void setup() {
  pinMode(TRIG, OUTPUT);
  digitalWrite(TRIG, LOW);
  pinMode(ECHO, INPUT);
  Serial.begin(115200);
  Serial.println(F("Nivel de agua | V = guardar vacio (0%) | L = guardar lleno (100%)"));
}

void loop() {
  char comando = 0;
  while (Serial.available()) {
    const char c = Serial.read();
    if (c == 'v' || c == 'V' || c == 'l' || c == 'L') comando = c;
  }

  const float distancia = medirCm();
  if (distancia < 0.0f) {
    Serial.println(F("Sin lectura valida. Revisa conexion y orientacion."));
  } else {
    if (comando == 'v' || comando == 'V') {
      vacio = distancia;
      Serial.print(F("Vacio guardado: "));
      Serial.println(vacio, 2);
    } else if (comando == 'l' || comando == 'L') {
      if (distancia < 5.0f || vacio - distancia < 3.0f) {
        Serial.println(F("No se guardo lleno: primero envia V y deja al menos 5 cm libres sobre el agua."));
      } else {
        lleno = distancia;
        Serial.print(F("Lleno guardado: "));
        Serial.println(lleno, 2);
      }
    }

    Serial.print(F("Distancia: "));
    Serial.print(distancia, 1);
    Serial.print(F(" cm | "));
    if (lleno >= 5.0f && vacio - lleno >= 3.0f) {
      const float nivel = constrain(100.0f * (vacio - distancia) / (vacio - lleno), 0.0f, 100.0f);
      Serial.print(F("Nivel: "));
      Serial.print(nivel, 1);
      Serial.println(F(" %"));
    } else {
      Serial.println(F("Pendiente: calibra con V y luego L."));
    }
  }
  delay(500);
}
