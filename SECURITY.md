# Security policy

## Report a security problem privately

Use GitHub's private form: **[Report a vulnerability](https://github.com/sudokhaled/just-in-case/security/advisories/new)**. Only the maintainers can see it. Please do not open a public issue until it is fixed.

Tell us:

- which part is affected (firmware, Raspberry Pi server, website, build tool or a workflow) and which release,
- how to reproduce it,
- what an attacker could do with it.

We aim to reply within 7 days and to fix or publish a plan within 30 days. With your permission, we will credit you in the release notes.

## What counts

- **Hotspot firmware** (`hardware/esp32/`) and the **Raspberry Pi server** (`hardware/raspberry-pi/`): anything that lets someone on the WiFi network change the library, take over the device, or reach the network behind it.
- **Build tool and workflows** (`tools/`, `.github/`): anything that could slip altered content or code into the downloads, the website or the flash images.
- **Website and offline app**: anything that runs a script the visitor did not expect.

## What does not count

- **Wrong or dangerous information in an article.** This is urgent, but it should be public so it gets fixed and seen fast. Use the [error report form](https://github.com/sudokhaled/just-in-case/issues/new?template=error-report.yml).
- **The hotspot WiFi is open, with no password.** This is on purpose, so anyone in a crisis can join. Everything it serves is public anyway. To require a password, set `AP_PASSWORD` (ESP32) or `PASSWORD` (Raspberry Pi), as their guides explain.
- **The hotspot answers every web address with the library.** This captive portal is how phones find it.

The hotspots serve read-only files. They have no uploads, no accounts, and collect no personal data.

## Supported versions

Fixes go into the `main` branch and the next release. Devices running older firmware should be flashed with the latest release.

Every release includes `SHA256SUMS.txt` so you can check that downloads were not changed.
