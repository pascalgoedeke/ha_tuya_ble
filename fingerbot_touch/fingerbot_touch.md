## Fingerbot Touch Teardown (bs3ubslo)

I initially created this fork because I wanted to control a Fingerbot Touch (see image below) locally using Home Assistant.
The device itself only has Bluetooth. There are WiFi hubs available for it but that seems unnecessary. It's also not a good idea to provide these devices with an internet connection from a security and privacy point of view.

<p align="center">
  <img src="1.jpg" alt="Fingerbot Touch packaging" width="500">
</p>

I did use the device and this integration for some time, however, it didn't turn out to be as snappy and reliable as I had hoped.
I also didn't like the touch buttons on the device itself but that's personal preference.
This is why I took matters into my own hand and built my own Fingerbot Touch device using ESPHome and the "fingers" of the original.
You can find out more about my own creation below but I first had to take the original Fingerbot apart.

<p align="center">
  <table>
    <tr>
      <td><img src="2.jpg" width="300" /></td>
      <td><img src="3.jpg" width="300" /></td>
      <td><img src="4.jpg" width="300" /></td>
    </tr>
    <tr>
      <td><img src="5.jpg" width="300" /></td>
      <td><img src="6.jpg" width="300" /></td>
      <td><img src="7.jpg" width="300" /></td>
    </tr>
  </table>
</p>

Opening the case did require quite a bit of brute force. Inside, the device was neatly packed and basically as small as it could be considering the battery.
There are two cables connecting to the fingers on the outside, two wires for the internal touch buttons (copper foil) and a battery connector.
The interesting part: The fingers themselves have two wires each and it's enough to provide 3.3 V across them to power the touch functionality and the built-in LED.
This makes it very easy to control them using an ordinary microcontroller. No special driver required.
I believe you would even be okay without an additional resistor as there seems to be one built-in but I've just been using an extra 220 Ω resistor and it's working nicely.

On the PCB, there is nothing surprising: The main chip (Beken BK3432 2.4 GHz Bluetooth 4.2 / 5.0 Dual Mode / BLE with integrated microcontroller RM968E, flash storage and RAM), 16 MHz quartz crystal, capacitive touch sensor (Holtek BS812C-1, labeled 12C-1), Li-ion battery charging controller (TP4057, labeled 57b4), voltage controller for 3 V (XC6206P302MR, labeled 65Z5) as well as the MOSFET transistors to trigger the fingers.

<p align="center">
  <table>
    <tr>
      <td><img src="8.jpg" width="300" /></td>
      <td><img src="9.jpg" width="300" /></td>
      <td><img src="10.jpg" width="300" /></td>
    </tr>
    <tr>
      <td><img src="11.jpg" width="300" /></td>
      <td><img src="12.jpg" width="300" /></td>
    </tr>
  </table>
</p>

### My own Fingerbot

Lastly, I've quickly thrown together a PCB and 3D printed enclosure for my own Fingerbot. I'm using a XIAO-ESP32-C6 flashed with ESPHome.
It is connected via Thread (but WiFi would also be possible). I always suggest using an external antenna (one of the reasons I prefer the XIAOs over Tenstar Minis).
I've also added some flat LED buttons, one for the finger and one for Home Assistant automations.
As the device is fully USB-powered, no battery is required and we don't have to be too conservative with power which allows for quick and snappy control.

The PCB was manufactured by [AISLER](https://aisler.net/). They are EU-based and a great alternative to Chinese manufacturers.
If you [check them out](https://aisler.net/), feel free to drop me a message and I will send you my referral code for 10 € off.

<p align="center">
  <table>
    <tr>
      <td><img src="13.jpg" width="500" /></td>
      <td><img src="14.jpg" width="500" /></td>
    </tr>
  </table>
</p>

*Closing note:* For Busch Welcome intercoms specifically, there is a great project [Mat931/esp32-doorbell-bus-interface](https://github.com/Mat931/esp32-doorbell-bus-interface) that reverse engineered the bus communication and can offer doorbell notifications and remotely opening your door. 
