// Just In Case: the offline survival library on a WiFi hotspot.
//
// Any phone, tablet or laptop that joins the open network "JustInCase-Library"
// is shown the library automatically (captive portal), or can open
// http://192.168.4.1 in a browser. No internet, no app, no SIM card needed.
//
// Boards: any ESP32 (ESP32, -S2, -S3, -C3, -C6) or ESP8266 with 4 MB flash.
// Files: run `python3 tools/build.py` in the repository first. It fills the
// data/ folder next to this sketch with gzip-compressed pages. Upload that
// folder to the board's LittleFS file system (see README.md), or copy it to
// the root of a microSD card and set USE_SD_CARD to 1 (ESP32 only).
//
// Power: about 0.3-0.6 W. A 10,000 mAh power bank lasts 1.5 to 3 days.
//
// License: MIT. https://github.com/sudokhaled/just-in-case

#include <Arduino.h>
#include <DNSServer.h>
#include <LittleFS.h>

#if defined(ESP8266)
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
typedef ESP8266WebServer WebServerType;
#else
#include <WiFi.h>
#include <WebServer.h>
typedef WebServer WebServerType;
#endif

// ---- Settings ---------------------------------------------------------------
// Change the values below, or pass them as build flags (-DLOW_POWER=0).

// Network name people will see. Keep it obvious.
#ifndef AP_SSID
#define AP_SSID "JustInCase-Library"
#endif
// Empty = open network, so anyone can join in an emergency.
// Or set 8+ characters to require a password.
#ifndef AP_PASSWORD
#define AP_PASSWORD ""
#endif
#ifndef AP_CHANNEL
#define AP_CHANNEL 6
#endif
// ESP32 allows up to 10 phones at once, ESP8266 up to 8.
#ifndef AP_MAX_CLIENTS
#define AP_MAX_CLIENTS 8
#endif

// 1 = lower transmit power and CPU speed: about 30% less power, range about
// 20-30 m (65-100 ft). It also fixes unstable WiFi on many tiny ESP32-C3
// "SuperMini" boards. 0 = maximum range.
#ifndef LOW_POWER
#define LOW_POWER 1
#endif

// 1 = read files from a microSD card instead of internal flash (ESP32 only).
// Wire the card reader to the board's default SPI pins.
#ifndef USE_SD_CARD
#define USE_SD_CARD 0
#endif
#ifndef SD_CS_PIN
#define SD_CS_PIN 5
#endif

// ---- End of settings --------------------------------------------------------

#if USE_SD_CARD && defined(ESP8266)
#error "USE_SD_CARD is only supported on ESP32 boards"
#endif
#if USE_SD_CARD
#include <SD.h>
#include <SPI.h>
#endif

static const IPAddress kApIp(192, 168, 4, 1);
static const IPAddress kNetmask(255, 255, 255, 0);
static const byte kDnsPort = 53;

DNSServer dns;
WebServerType server(80);
fs::FS *files = nullptr;

static const char kNoFilesPage[] PROGMEM =
    "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
    "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
    "<title>Just In Case</title></head><body style=\"font-family:sans-serif;max-width:40rem;margin:auto;padding:16px\">"
    "<h1>Just In Case</h1><p>The hotspot works, but the library files are missing.</p>"
    "<p>On a computer: run <code>python3 tools/build.py</code>, then upload the "
    "<code>data</code> folder to this board (see hardware/esp32/README.md).</p></body></html>";

String contentType(const String &path) {
  if (path.endsWith(".html")) return F("text/html; charset=utf-8");
  if (path.endsWith(".css")) return F("text/css");
  if (path.endsWith(".js")) return F("application/javascript");
  if (path.endsWith(".json")) return F("application/json");
  if (path.endsWith(".webmanifest")) return F("application/manifest+json");
  if (path.endsWith(".txt")) return F("text/plain; charset=utf-8");
  if (path.endsWith(".epub")) return F("application/epub+zip");
  if (path.endsWith(".svg")) return F("image/svg+xml");
  if (path.endsWith(".png")) return F("image/png");
  if (path.endsWith(".ico")) return F("image/x-icon");
  return F("application/octet-stream");
}

// Requests for any other host name are captive-portal checks from phones
// (connectivitycheck.gstatic.com, captive.apple.com, msftconnecttest.com...)
// or sites typed by the user. Send them all to the library's front page.
bool isForUs() {
  String host = server.hostHeader();
  int colon = host.indexOf(':');
  if (colon >= 0) host = host.substring(0, colon);
  return host.length() == 0 || host == kApIp.toString();
}

void redirectHome() {
  server.sendHeader(F("Location"), String(F("http://")) + kApIp.toString() + F("/"), true);
  server.sendHeader(F("Cache-Control"), F("no-store"));
  server.send(302, F("text/plain"), "");
}

// Streams a file in small chunks so it works with very little RAM.
bool sendFile(const String &path, const String &type, bool gzipped) {
  File f = files->open(path, "r");
  if (!f || f.isDirectory()) return false;
  server.setContentLength(f.size());
  if (gzipped) server.sendHeader(F("Content-Encoding"), F("gzip"));
  server.sendHeader(F("Cache-Control"), F("max-age=3600"));
  server.send(200, type, "");
  if (server.method() != HTTP_HEAD) {
    uint8_t buf[1024];
    WiFiClient client = server.client();
    size_t n;
    while ((n = f.read(buf, sizeof(buf))) > 0) {
      if (client.write(buf, n) != n) break;  // The phone went away.
      yield();
    }
  }
  f.close();
  return true;
}

void handleRequest() {
  if (!isForUs()) {
    redirectHome();
    return;
  }
  String path = server.uri();
  if (path.indexOf("..") >= 0) {
    server.send(400, F("text/plain"), F("Bad request"));
    return;
  }
  if (path.endsWith("/")) path += F("index.html");
  if (path.lastIndexOf('.') <= path.lastIndexOf('/')) path += F(".html");

  // Pages are stored compressed (.gz) to fit in flash; every browser accepts gzip.
  String type = contentType(path);
  String gz = path + F(".gz");
  if (files && files->exists(gz) && sendFile(gz, type, true)) return;
  if (files && files->exists(path) && sendFile(path, type, false)) return;

  if (path == F("/index.html")) {
    server.send_P(200, "text/html; charset=utf-8", kNoFilesPage);
    return;
  }
  redirectHome();
}

bool mountFiles() {
#if USE_SD_CARD
  if (SD.begin(SD_CS_PIN)) {
    files = &SD;
    return true;
  }
  Serial.println(F("SD card not found. Falling back to internal flash."));
#endif
#if defined(ESP8266)
  bool ok = LittleFS.begin();
#else
  bool ok = LittleFS.begin(false);
#endif
  if (ok) files = &LittleFS;
  return ok;
}

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println();
  Serial.println(F("Just In Case library hotspot"));

#if LOW_POWER && !defined(ESP8266)
  setCpuFrequencyMhz(80);  // The lowest speed at which WiFi still runs.
#endif

  if (!mountFiles()) {
    Serial.println(F("No file system found: upload the data folder (see README)."));
  } else if (!files->exists(F("/index.html.gz")) && !files->exists(F("/index.html"))) {
    Serial.println(F("File system is empty: upload the data folder (see README)."));
  }

  WiFi.mode(WIFI_AP);
  WiFi.softAPConfig(kApIp, kApIp, kNetmask);
  const char *password = strlen(AP_PASSWORD) >= 8 ? AP_PASSWORD : nullptr;
  if (!WiFi.softAP(AP_SSID, password, AP_CHANNEL, false, AP_MAX_CLIENTS)) {
    Serial.println(F("Could not start the hotspot. Restarting."));
    delay(3000);
    ESP.restart();
  }
#if LOW_POWER
#if defined(ESP8266)
  WiFi.setOutputPower(10.0);  // dBm
#else
  WiFi.setTxPower(WIFI_POWER_8_5dBm);
#endif
#endif

  dns.setErrorReplyCode(DNSReplyCode::NoError);
  dns.start(kDnsPort, "*", kApIp);  // Every name points to us.

  server.onNotFound(handleRequest);
  server.begin();

  Serial.print(F("Join WiFi \""));
  Serial.print(F(AP_SSID));
  Serial.print(F("\" and open http://"));
  Serial.println(kApIp);
}

void loop() {
  dns.processNextRequest();
  server.handleClient();
  delay(2);  // Lets the chip idle between requests, which saves power.
}
