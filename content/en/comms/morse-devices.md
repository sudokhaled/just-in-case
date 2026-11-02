---
title: Sending and Receiving Morse With What You Have
summary: Build a 2-way wired telegraph, a key and a practice buzzer from scrap, signal with lamps and headlights, and learn to read Morse code by ear and by eye.
priority: important
order: 40
tags: morse, morse code, telegraph, telegraphy, wired telegraph, morse key, telegraph key, straight key, buzzer, practice oscillator, code practice oscillator, sounder, signal lamp, signalling lamp, signaling lamp, aldis lamp, shutter, flashlight, torch, headlights, light signal, blinker, cw, dit dah, koch method, farnsworth, learn morse, copy morse, two houses, between tents, wire, earth return, battery circuit, 555 timer, laser, no signal, no network, no phone
reviewed: no
updated: 2026-11-01
---

> [!CAUTION]
> **Never aim a laser at an aircraft, a driver or a person,** and never dazzle drivers or pilots with bright lights. A laser pointer can blind a pilot and is a serious crime in many countries. Flashing headlights at drivers can cause a crash.
>
> **Low-voltage batteries only.** Never connect a telegraph to mains power, telephone lines or an electric fence: they carry dangerous voltages. Disconnect long outdoor wires when you hear thunder.
>
> **Never string a wire across a road or path at neck height.** It can kill a cyclist or motorcyclist. Bury it, or run it high overhead.

## Quick steps

1. **Agree first** with the other person: a fixed time to signal (for example 20:00 for 10 minutes), who calls first, and a few 2-letter codes written on a card, such as OK = all well.
2. **By light:** point a flashlight at the other person. Cover and uncover the lens with your hand or a card. A short flash is about half a second, a long flash about 1.5 seconds.
3. **By wire:** each place needs a 3 to 9 V battery (both the same voltage), a buzzer, and a key whose lever rests on one contact and touches a second contact when pressed. Run 2 insulated wires between the places:
   - Wire 1 joins the 2 key levers.
   - Wire 2 joins the minus side of both batteries and of both buzzers.
   - At each place, the rest contact goes to the buzzer's plus side, and the pressed contact goes to the battery's plus side. Pressing one key sounds the other place's buzzer.
4. **To receive:** write each letter down as soon as you recognize it. If you miss one, leave a gap and keep going.
5. **When you have the whole message,** send R (short, long, short) to say "received".
6. **Practice every day** for 10 to 30 minutes with a buzzer and key. Most people can read slow Morse after a few weeks.

## Which method to use

| Method | Range | Needs | Works by day | Private |
|---|---|---|---|---|
| Flashlight or lamp | Several km at night | Line of sight | Poorly | No: anyone in view can read it |
| Mirror in sunlight | Tens of km | Sun, line of sight | Yes | No |
| Sound (whistle, horn) | Hundreds of meters | Quiet air | Yes | No |
| Wired telegraph | Up to about 1 to 2 km | Wire, 2 batteries, 2 buzzers, 2 keys | Yes | Yes, unless the wire is tapped |

For the code itself, timing, SOS and sound signals, see [Morse Code and Signal Codes](../comms/morse-code.md).

## A wired telegraph between 2 houses or tents

This circuit lets either person send, and the other person's buzzer sounds. Each station has its own battery, buzzer and key. Only 2 wires join them.

```
 STATION A                        STATION B

 +--[BUZZER]--U              U--[BUZZER]--+
 |             \            /             |
 |              L--WIRE 1--L              |
 |                                        |
 |              D          D              |
 |              |          |              |
 +--[- BATT +]--+          +--[+ BATT -]--+
 |                                        |
 +----------------- WIRE 2 ---------------+

 L = key lever (springs up onto U at rest)
 U = rest contact     D = press contact
```

### What you need

- **2 batteries of the same voltage,** 3 to 9 V: 2 to 6 AA cells in a holder, a 9 V battery, or a 6 V lantern battery.
- **2 buzzers:** small "active" piezo buzzers (marked + and -, rated 3 to 12 V) are best. They use little current and make a tone from a battery. Battery doorbell buzzers also work.
- **Or 2 LEDs** instead of buzzers, each with a resistor in series: 330 to 470 ohms for 9 V, 150 to 220 ohms for 4.5 V.
- **2 two-way keys,** made from scrap.
- **2 insulated wires:** speaker wire, bell wire or telephone cable.

### Building it

1. **Test it on a table first,** with short wires.
2. At each station, connect the buzzer between U and the return point, and the battery between D and the return point. At both stations, battery plus goes to D.
3. Connect the plus side of active buzzers or LEDs (the long leg of an LED) to U.
4. Connect wire 1 between the 2 levers (L) and wire 2 between the 2 return points.
5. Press key A. Buzzer B must sound. Then test key B.
6. **Do not both press at once:** nothing sounds. The receiver waits until the sender sends K (long, short, long) for "your turn".

### Wire and range

- **With 9 V and active buzzers,** ordinary 2-core wire works up to about 1 to 2 km (0.6 to 1.2 miles). Thin wire, loose joints and rust shorten this.
- **Earth return:** you can replace wire 2 with a metal rod driven at least 1 m (3 ft) into damp soil at each end. It works in wet soil, but in dry, sandy or rocky ground it may not work at all.
- Bare wire touching wet ground, trees or metal leaks the current. Use insulated wire, or hang bare wire on plastic bottle necks.
- Run the wire along fences and walls, far from power lines. Under paths, bury it in a shallow trench. Over roads, keep it at least 5 m (16 ft) high.
- **Simple on-off keys only?** Build 2 separate one-way circuits instead: one battery, one key and one buzzer each, in a loop. This needs 4 wires, or 3 if both circuits share the return wire.

## Making a key from scrap

### Two-way lever key (for the telegraph)

1. Take a wooden block about 15 x 8 cm (6 x 3 in).
2. Cut a springy metal strip about 10 cm (4 in) long and 1 to 2 cm (half an inch) wide: steel packing strap, a flat spring from an old device, or tin can metal folded double. **Can edges are sharp:** fold or file them.
3. Screw one end of the strip to the block, with a wire under the screw. This is the lever, L. Bend it so the free end rises about 1 cm (half an inch).
4. Drive a screw under the free end so the head sits 3 mm (1/8 in) below the strip. Put a wire under its head. This is D.
5. Fix a bent metal bracket or a large nail over the free end so the strip springs up against it at rest. Put a wire on it. This is U.
6. Glue a bottle cap or cork on the free end as a button. Scrape the contacts clean.

### Simple on-off keys

- **Clothes peg:** wrap aluminium foil around the 2 handle ends, the parts you squeeze. Connect a wire to each foil. Squeeze, and the foil pieces touch.
- **Strip key:** build the lever key, but leave out the bracket (step 5).

## A practice oscillator for learning

- **Simplest:** put a battery, a simple key and an active buzzer in a loop. Press the key and it beeps.
- Active buzzers give a high, sharp tone of 2,000 to 4,000 Hz. Many people find a lower tone of 500 to 800 Hz easier for long practice.
- **Lower tone with a 555 timer chip** (from old electronics or a parts kit), powered by 5 to 9 V:
   1. Connect pins 4 and 8 to plus, through the key.
   2. Connect pin 1 to minus.
   3. Connect a 1 kilohm resistor between pin 8 and pin 7, and a 10 kilohm resistor between pin 7 and pin 6.
   4. Join pins 6 and 2. Connect a 100 nF (0.1 microfarad) capacitor from pin 2 to minus.
   5. Connect pin 3 to the plus side of a 100 microfarad capacitor. Connect its minus side through a 100 ohm resistor to a small speaker, and the speaker's other wire to minus.
   6. The tone is about 700 Hz. A larger resistor between pins 7 and 6 lowers it.

## Signaling with lamps

- **Flashlight:** cover and uncover the lens. This is faster and saves the switch. LED flashlights can also be switched directly.
- **Shutter:** for a candle, oil lamp, fire or old-style bulb, which cannot flash quickly. Put the light behind a board with a hole, and open and close a hinged card flap over the hole.
- **Lamp behind a board:** raise and lower a board or blanket in front of a lit window or lantern. It is slow but visible from far away at night.
- **Car headlights:** flash the main beam. They use a lot of power: keep messages short. Never point them at a road.
- **Speed:** send slowly, with a short flash of about half a second and clear gaps between letters.

### Reading light signals

- **At night:** watch from a dark place. Rest your eyes on the light. Binoculars help, held steady on a wall or post.
- **In daylight:** a flashlight is hard to see beyond a few hundred meters. Use a mirror in sunshine (see [Signaling for Rescue](../navigation/signal-rescue.md) for aiming), or a large white board swung against a dark background.
- **Work in pairs:** one person watches and calls out "dit" and "dah". The other writes them down and splits them into letters at the gaps.

## Learning to receive

1. **Learn by sound, never from a printed chart.** Hear each letter as one rhythm. Do not count the dots.
2. **Write each letter the moment you recognize it.** If you miss one, write a short dash and keep going. Do not stop to think.
3. **Use the Koch method:** letters are sent at full speed from the first day, about 15 to 20 words per minute. Start with only 2 letters. Add 1 new letter each time you copy at least 90% correctly.
4. **Or use Farnsworth spacing:** letters are sent at full speed, but the gaps between letters and words are made long, so the overall speed is slow. Shorten the gaps as you improve.
5. **Practice in short sessions:** 10 to 30 minutes, once or twice a day. In the 1930s trials of Ludwig Koch, half-hour lessons worked best.

**Realistic time:** with daily practice, most adults copy 5 words per minute in a few weeks and 10 to 12 words per minute in about 2 to 4 months. Koch's classes needed about 12 to 14 hours of lessons in total. Most people learning alone take longer.

### A two-person drill

1. Person A sends 5 groups of 5 random letters from the letters learned so far. Person B writes them down.
2. Compare, repeat any missed letter, then swap roles.
3. When both copy 90% correctly, add names, numbers, real messages and your agreed codes.

### Agreed codes and schedules

Make a code card for each station before you need it. Use 2-letter codes that do not look like SOS or each other.

| Code | Meaning |
|---|---|
| OK | All well here |
| WA | We need water |
| MD | We need medical help |
| DG | Danger: stay away |
| CM | Come here now |
| NX | Nothing new, next signal at the usual time |

- Give each station a call letter, for example A and B. Start every message with the station you call, then DE ("from"), then your letter: "B DE A".
- Agree a fixed time and a backup time, for example 20:00 and 20:30.
- Number your messages. A lost number shows a lost message.

## Morse by radio

- **Sending Morse by radio needs a licensed radio and an amateur radio licence,** except in a real life-or-death emergency. Then you may use any radio to call for help. See [Emergency Radio](../comms/emergency-radio.md).
- **Hearing Morse on radio needs a receiver with SSB or a BFO.** An ordinary AM or FM radio hears nothing but clicks. See [Building and Improvising Radios](../comms/build-radio.md).

## Light and sound safety

- **Never aim a laser at aircraft, drivers or people.** It can blind them. In the US, aiming a laser at an aircraft can bring up to 5 years in prison, and the UK has similar penalties.
- **Do not dazzle drivers or pilots.** Signaling a search aircraft is fine while it is far away. Stop when it comes close or lands.
- **In a conflict zone,** a light or sound signal shows where you are. Signal only when you are sure who will see it.
- Do not hold a buzzer or horn against your ear.

## Sources

- International Telecommunication Union (ITU), *Recommendation ITU-R M.1677-1: International Morse Code*, 2009.
- Pierpont W. G., *The Art and Skill of Radio-Telegraphy*, 2002 (chapter on Koch's method).
- ARRL, *The ARRL Handbook for Radio Communications*, 2024.
- US Army, *ATP 6-02.53 Techniques for Tactical Radio Operations*, 2020 (public domain).
- US Code, *18 U.S.C. 39A: Aiming a laser pointer at an aircraft*.
- UK Parliament, *Laser Misuse (Vehicles) Act 2018*.
- Texas Instruments, *xx555 Precision Timers* data sheet (SLFS022), 2014.
