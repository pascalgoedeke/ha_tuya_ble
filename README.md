# Home Assistant support for Tuya BLE devices

## Overview

This integration supports Tuya devices locally connected via BLE.

It includes support for **Fingerbot Touch** (product_id 'bs3ubslo') and is primarily maintained for use with Fingerbots.

**Note on Battery Saving:** These devices usually enter sleep mode after 5 minutes of inactivity.
To prevent battery drain, automatic reconnection is disabled.
The connection will reestablish automatically when an action is triggered (potentially introducing a slight delay).
You can also use the provided Home Assistant connection status entities and reconnect / reload buttons to reconnect manually.

## Installation

Place the `custom_components` folder in your configuration directory (or add its contents to an existing `custom_components` folder). Alternatively install via [HACS](https://hacs.xyz/).

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=pascalgoedeke&repository=ha_tuya_ble&category=integration)

## Usage

After adding to Home Assistant integration should discover all supported Bluetooth devices, or you can add discoverable devices manually.

The integration works locally, but connection to Tuya BLE device requires device ID and encryption key from Tuya IOT cloud.
To obtain the credentials, please refer to *old* official Tuya integration [documentation](https://web.archive.org/web/20240204064157/https://www.home-assistant.io/integrations/tuya/).

## Credits

_Inspired by code of [@redphx](https://github.com/redphx/poc-tuya-ble-fingerbot)_

_Original HASS component forked from https://github.com/PlusPlus-ua/ha_tuya_ble_

_Merged several changes by @airy10 and @patriot1889, including light support, forked from https://github.com/garnser/ha_tuya_ble_

## Supported devices list

* Fingerbots (category_id 'szjqr')
  + Fingerbot (product_ids 'ltak7e1p', 'y6kttvd6', 'yrnk7mnn', 'nvr2rocq', 'bnt7wajf', 'rvdceqjh', '5xhbk964'), original device, first in category, powered by CR2 battery.
  + Adaprox Fingerbot (product_id 'y6kttvd6'), built-in battery with USB type C charging.
  + Fingerbot Plus (product_ids 'blliqpsj', 'ndvkgsrm', 'yiihr7zh', 'neq16kgd'), almost same as original, has sensor button for manual control.
  + CubeTouch 1s (product_id '3yqdo5yt'), built-in battery with USB type C charging.
  + CubeTouch II (product_id 'xhf790if'), built-in battery with USB type C charging.

  All features available in Home Assistant, programming (series of actions) is implemented for Fingerbot Plus.
  For programming exposed entities 'Program' (switch), 'Repeat forever', 'Repeats count', 'Idle position' and 'Program' (text). Format of program text is: 'position[/time];...' where position is in percents, optional time is in seconds (zero if missing).

* Fingerbots (category_id 'kg')
  + Fingerbot Plus (product_ids 'mknd4lci', 'riecov42').
  + Fingerbot Switch Robot (product_id '4ctjfrzq').
  + Fingerbot Touch (product_id 'bs3ubslo').

* Temperature and humidity sensors (category_id 'wsdcg')
  + Soil moisture sensor (product_id 'ojzlzzsw').
  + Soil Thermo-Hygrometer (product_id 'tv6peegl').

* CO2 sensors (category_id 'co2bj')
  + CO2 Detector (product_id '59s19z5m').

* Smart Locks (category_id 'ms')
  + Smart Lock (product_ids 'ludzroix', 'isk2p555', 'gumrixyt', 'uamrw6h3').
  + TEKXDD Fingerprint Smart Lock (product_id 'okkyfgfs').

* Climate (category_id 'wk')
  + Thermostatic Radiator Valve (product_ids 'drlajpqc', 'nhj2j7su', 'zmachryv').

* Smart water bottle (category_id 'znhsb')
  + Smart water bottle (product_id 'cdlandip').

* Smart Water Valve (category_id 'sfkzq')
  + Smart Water Valve (product_id 'nxquc5lb').

* Irrigation computer (category_id 'ggq')
  + Irrigation computer (product_id '6pahkcau').
  + 2-outlet irrigation computer SGW02 (product_id 'hfgdqhho'), also known as MOES BWV-YC02-EU-GY.

* Lights (category_id 'dd')
  + LGB102 Magic Strip Lights (product_id 'nvfrtxlq').
  + Most light products should be supported as the Light class tries to get device description from the cloud when they are added.

* Smart Bulbs (category_id 'dj')
  + SSG Smart 9W (product_id 'u4h3jtqr').

## Support project
_The following is a comment from the original developer which deserves to stay_


I am working on this integration in Ukraine. Our country was subjected to brutal aggression by Russia. The war still continues. The capital of Ukraine - Kyiv, where I live, and many other cities and villages are constantly under threat of rocket attacks. Our air defense forces are doing wonders, but they also need support. So if you want to help the development of this integration, donate some money and I will spend it to support our air defense.
<br><br>
<p align="center">
  <a href="https://www.buymeacoffee.com/3PaK6lXr4l"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy me an air defense"></a>
</p>
