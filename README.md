# Hindsight
Look back on your digital experience with Hindsight! (very alpha)
---

## Overview
Hindsight is an android app that takes a screenshot every 2 seconds. The server upload functionality allows a user to upload the screenshots to a server running on their personal computer.

## Setup
### Server
1) Install conda if you don't have it already
2) Run: `conda create --name "hindsight" --file hindsight_server_req.txt`
3) Openssl is used to create ssl keys for running the server over Https. The keys are expected in `$Home/.hindsight_server` but that can be changed in `hindsight_server/hindsight_server.py`. Copy `hindsight_server/template_san.cnf` to `$Home/.hindsight_server/san.cnf` and fill in the `${}` sections. 
4) Run `openssl req -new -nodes -keyout server.key -out server.csr -config san.cnf`
5) Run `openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt -extensions v3_ca -extfile san.cnf`. You now have the public and private keys for running the server.
6) You need to generate a `.der` file for the app to authenticate the identify of the server. Run `openssl x509 -outform der -in server.crt -out hindsight_server.der`
7) You can change the directory that images are stored in by modifying `RAW_SCREENSHOTS_DIR` at the top of `hindsight_server/hindsight_server.py`
8) Run the server: `python hindsight_server.py`

### App
1) Open `hindsight_android` in Android Studio.
2) In `hindsight_android/app/src/main/java/com/connor/hindsight/network/RetrofitClient.kt` change `BASE_URL` to the base url of your server. This should be printed out when `python hindsight_server.py` is run and should also be the ip of `${computer ip}` in the `san.cnf`.
3) Move `hindsight_server.der` into `hindsight_android/app/src/main/res/raw/`
4) You should be good to run the app on your device!

## Interface
Currently the app has 2 "working" functionalities.
1) You can toggle on and off the screen recording.
2) You can upload you screenshots to your server by clicking `Server Upload`

## Settings
Currently there is only one setting and it is called `Only Take Screenshot when User is Active`. This setting is recommended as (depending on your phone usage) it can signifantly save battery life. When active, the app will only take a screenshot if the user has been active since the last screenshot.

## Permissions
* The App requires screen broadcasting each time recording is restarted. This should ideally only be needed if the phone is turned off or if the user intentionally stops recording (pausing is available as well). However, the app is very buggy so it may be required more often.
* In order to use the `Only Take Screenshot when User is Active` setting and for the screenshot to be saved with the name of the application running, Accessibility access is required. Unfortunetly, this is the only robust way I could find to introduce this functionality.

## Contributions
I'm very interested in what people think about the project so feel free to reachout if you have thoughts or are interested in helping out!

## Considerations
1) Lots of security concerns so would love feedback in that area!
2) Currently it uses around 7% of my new google pixel8's battery. Hopefully this can be reduced even more and I'm very curious if battery life will be too big of a limitation for other phones.