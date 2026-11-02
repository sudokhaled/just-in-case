---
title: Text Messages Without Internet: Mesh Radios and Phones
summary: Send text messages with no phone network using licence-free LoRa mesh radios such as Meshtastic, phone-to-phone apps and walkie-talkies, and keep messages short, clear and private.
priority: important
order: 50
tags: mesh, mesh network, mesh radio, lora, meshtastic, meshcore, text messages, texting, sms, chat, off grid messaging, off-grid, no signal, no network, no internet, no phone, no mobile, no cell service, phone down, network down, 868 mhz, 915 mhz, 433 mhz, licence free, license free, relay, repeater, node, solar node, bluetooth, wi-fi, wifi, wi-fi direct, hotspot, briar, peer to peer, walkie talkie, two-way radio, pmr446, frs, cb radio, encryption, privacy
reviewed: no
updated: 2026-11-01
---

> [!CAUTION]
> **Assume anyone can read or hear your messages** unless you set up a private encrypted channel. Never send where food, medicine or money is stored, which homes are empty, or where vulnerable people are, on an open channel.
>
> **Set up mesh radios and phone apps before a crisis.** Without internet you cannot download the app, update the radio or add new contacts at a distance.
>
> **Do not rely on one method.** Mesh radios fail when batteries run flat or when there is no relay in range. Keep a paper plan with meeting places and times.

## Quick steps

1. **Get at least 2 LoRa mesh radios** (for example Meshtastic devices) for your region's band: **868 MHz** in Europe, **915 MHz** in the Americas and Australia, **865 to 867 MHz** in India. Use only the band legal where you are.
2. **Pair each radio with a phone** by Bluetooth using the free Meshtastic app. **Set the region first:** the radio does not transmit until you do.
3. **Keep the default public channel** so you can reach strangers in an emergency. Add a second, private channel with a random key for your group, and share it by scanning its QR code in person.
4. **Place one radio as high as you can,** antenna upright, on a roof, tower or hill, with a solar panel and battery. It relays messages for everyone else.
5. **Send short messages:** who, where, what, what you need, and when you will check again. Example: "Ana, Hill Farm: 4 people OK, need insulin by Friday. Next check 19:00."
6. **No mesh radios?** Phones can pass messages over Bluetooth or Wi-Fi only with an app such as Briar installed beforehand, and only over tens of meters. For voice, use licence-free walkie-talkies. In a real life-or-death emergency, any radio may be used to call for help.

## Which method to use

| Method | Range per hop | Needs | Battery life | Cost | Can relay |
|---|---|---|---|---|---|
| LoRa mesh radio (Meshtastic) | 1 to 10 km, much farther from hilltops | A radio for your band, usually a phone | 1 day to 2 weeks per 18650 cell | About US$25 to 100 each | Yes, up to 7 hops |
| Phone app over Bluetooth or Wi-Fi (Briar) | Tens of meters | App installed and contacts added before | Phone drains faster | Free with phones you own | Limited: messages pass when phones meet |
| Local Wi-Fi hotspot | 30 to 100 m | A phone, router or small board | Hours on a phone, days on a big battery | Free to low | No |
| Licence-free walkie-talkie | 1 to 5 km | 2 radios on the same channel | 1 to 3 days of light use | About US$20 to 60 a pair | No, only by people passing messages on |
| CB radio (27 MHz) | A few km, 5 to 20 km between good fixed antennas | Radio and a large antenna | Needs a 12 V battery for a fixed set | About US$50 to 150 | No |
| Runner or cyclist | Any distance | A trusted person | None | Free | Yes |

Ranges are typical, not promised. Hills, buildings and trees cut them. Height increases them.

## LoRa mesh radios (Meshtastic)

### What they are

- A LoRa mesh radio is a small, cheap, battery-powered radio that sends **short text messages** on licence-free bands.
- Each radio (a "node") **relays** messages it hears. A message can hop from node to node across a town or valley, with no phone network and no internet.
- **Meshtastic** is free, open-source software used on many of these radios. Most are controlled from a phone app over Bluetooth. Some models have their own screen and keyboard.
- Messages are short: about 200 characters. LoRa is slow: it cannot carry voice, photos or large files.
- Other LoRa mesh systems exist, for example MeshCore. They cannot talk to Meshtastic. Everyone in your group must use the same system.

### Licence-free bands by region

| Region | Band | Notes |
|---|---|---|
| Europe | 868 MHz (869.4 to 869.65 MHz) | Each radio may transmit at most 10% of the time; the software enforces this |
| Europe, some other countries | 433 MHz (433 to 434 MHz) | Short range with small antennas; also limited to 10% of the time |
| USA, Canada, much of Latin America | 915 MHz (902 to 928 MHz) | Brazil uses 902 to 907.5 MHz |
| Australia, New Zealand | 915 MHz (915 to 928 MHz) | |
| India | 865 to 867 MHz | |
| China | 470 to 510 MHz | |
| Japan, Korea, Taiwan, parts of Southeast Asia | 920 to 925 MHz | Exact limits differ by country |

**Check local rules.** Buy a radio and antenna made for your band: a 915 MHz radio cannot talk to an 868 MHz radio, and using the wrong band can be illegal.

### Range: be honest with yourself

- Between 2 handheld radios at chest height: about **1 to 3 km** in towns, **3 to 10 km** over open country.
- From a hilltop, tower or tall building to the ground: often **10 to 50 km**.
- Between 2 mountain tops with a clear view, links of more than 250 km have been made. Do not plan on this.
- Every relay node in the right place multiplies the range. One high node does more than 10 low ones.

### Power use and solar nodes

- Radios built on the **nRF52** chip use very little power: often **1 to 2 weeks** on one 18650 lithium cell (3,000 mAh) with the screen and GPS off.
- Radios built on the **ESP32** chip use about 10 times more: often **1 to 2 days** per 18650 cell.
- A fixed relay node can run day and night on a **1 to 3 W** solar panel (nRF52) or about **5 W** (ESP32), with 1 or 2 18650 cells. In cloudy or cold places, or in winter, use a bigger panel and more cells. These are figures from users, not promises.
- Turn off the screen, GPS and Wi-Fi on nodes that do not need them.
- **Never switch on a LoRa radio without its antenna.** It can damage the radio.
- For charging and lithium safety, see [Batteries: Use, Charge and Stay Safe](../power/batteries.md) and [Electricity Without the Grid](../power/off-grid-power.md).

### Setting up a group

1. **Install the Meshtastic app** on each phone and pair it with its radio by Bluetooth. Do this before a crisis.
2. **Set the region** (for example `EU_868`, `US` or `ANZ`). Until you set it, the radio does not transmit.
3. **Give each radio a short name** that your group will recognize, for example "ANA1".
4. **Keep the default modem setting** (LongFast) unless your whole area agrees to change it. Radios on different settings cannot hear each other.
5. **Keep the default primary channel.** Its key is public, so anyone with Meshtastic nearby can read it. That makes it useful for emergencies and useless for secrets.
6. **Add a private secondary channel** for your group. Give it a name and choose a random encryption key (AES-256).
7. **Share the private channel in person:** show its QR code and let each member scan it. Never send the key over an open channel.
8. **Send a test message** to each member and agree a check time.

### Placing a relay node high up

1. Choose the highest safe place with a clear view: a roof, mast, tower, tall tree or hilltop.
2. Use a weatherproof box. Put the antenna outside the box, upright.
3. Add a solar panel facing the sun at midday and a battery with charge protection.
4. Set its role to **ROUTER** only if it is fixed and high with a clear view over the area. Leave handheld and indoor radios as **CLIENT**. Too many routers waste airtime.
5. Keep it away from power lines. Do not climb in storms or high wind. Disconnect any antenna on a metal mast before a thunderstorm if you can reach it safely.

### Etiquette

- Keep the public channel for useful messages: news, warnings and requests for help.
- Do not set automatic messages, position reports or sensor reports to send often. Every message uses airtime for everyone.
- Leave the hop limit at its default of 3. Raise it only if messages cannot reach a far part of your group. The maximum is 7.
- Turn off position sharing on the public channel, or set it to a rough area only.
- Mark news as "confirmed" (with its source) or "not confirmed". Rumors spread fast on a mesh.

## Phones without a network

- **Some apps let phones message each other directly** over Bluetooth or Wi-Fi, with no mobile network. **Briar** is a well-known open-source example for Android.
- **Range is short:** tens of meters per hop, less through walls.
- **The app must be installed before the crisis.** In Briar, you add contacts by scanning each other's QR codes in person. Forum posts are passed on as members' phones come close to each other, so news spreads slowly.
- **Battery cost:** keeping Bluetooth and Wi-Fi searching drains the phone faster. Switch them on at agreed times.
- **Built-in file sharing** between nearby phones (AirDrop on Apple phones, Quick Share on Android) works without a network. It can pass a photo of a notice, a map or a list.
- **A local Wi-Fi hotspot**, from a phone or a small board running the Just In Case library, reaches about 30 to 100 m and could one day also host a simple shared message board for everyone nearby.

## Voice: walkie-talkies and CB

- **Licence-free walkie-talkies** (PMR446, FRS, UHF CB) carry voice over 1 to 5 km on flat ground, more from high places.
- **CB radio** on 27 MHz reaches a few kilometers between handhelds and farther with a car or house antenna.
- **"Privacy codes" on walkie-talkies do not make calls private.** They only filter what your radio lets you hear. Anyone on the channel can listen.
- For channels, emergency channels and how to make a distress call, see [Emergency Radio](../comms/emergency-radio.md).
- **Licensed amateur radio operators** can also send text and email-like messages by radio without internet. A licensed operator in your group is a big asset.

## Message discipline

- **Write the message first,** then send it. Keep it under about 200 characters.
- **Use a fixed order:** who, where, what happened, what you need, and when you will check again.
- **Be exact:** numbers, times, places. "3 adults, 1 child, 1 with broken leg" is better than "some people hurt".
- **Use a battery schedule.** Agree times to switch on phones and radios, for example 07:00 to 07:15 and 19:00 to 19:15. A Meshtastic node can stay on; the phone can stay off until the check time.
- **Confirm important messages.** Ask for a reply such as "received". Repeat numbers and names.
- **Keep a written log** of messages sent and received, with times. See [Organizing a Community](../community/community-groups.md).
- **Privacy:**
   - Assume anyone can read the public channel, and that radio signals can be traced to where they came from.
   - Use first names or agreed call signs, not full names and addresses.
   - In a conflict zone, transmit as little as possible and away from your shelter.
- **Write a paper backup** of channels, check times and meeting places for every family member. See [Family Emergency Plan](../reference/family-plan.md).

## Sources

- Meshtastic project, *LoRa Configuration* (region bands, duty cycle, hop limit), *Channel Configuration* (default and random keys), *Device Configuration* (roles) and *Radio Settings* (modem presets), meshtastic.org, accessed 2026.
- European Conference of Postal and Telecommunications Administrations (CEPT), *ERC Recommendation 70-03 Relating to the Use of Short Range Devices (SRD)*, 2024 edition.
- US Code of Federal Regulations, *47 CFR Part 15 (Radio Frequency Devices), section 15.247*, 2024.
- Australian Communications and Media Authority (ACMA), *Radiocommunications (Low Interference Potential Devices) Class Licence*, 2015.
- Briar Project, *Briar User Manual*, briarproject.org, accessed 2026.
- Electronic Communications Committee (ECC/CEPT), *ECC Decision (15)05 on PMR446*, 2015.
