# Hindsight <img src="https://github.com/cparish312/hindsight/blob/main/assets/hindsight_icon.png" width="40">

Look back on your digital experience with Hindsight! (very alpha)

---

## Overview
Hindsight is an android app that takes a screenshot every 2 seconds. The server upload functionality allows a user to upload the screenshots to a server running on their personal computer.

### Demo
<a href="https://www.loom.com/share/669eecf3c04648d4aae1565ead56273f">
    <img style="max-width:300px;" src="https://cdn.loom.com/sessions/thumbnails/669eecf3c04648d4aae1565ead56273f-with-play.gif">
</a>

## Setup
### Server
1) **Conda Environment:**
    *   Install [conda](https://docs.anaconda.com/free/miniconda/miniconda-install/) if you don't have it already
    *   Create the conda environment: `conda env create -f hindsight_server_env.yml`
    *   Activate the env using: `conda activate hindsight_server`
    *   If running on a Mac run `pip install ocrmac` to utilize OCR
2) **Initialization:**
    * Setup ngrok to allow querying over internet (Optional):
        * First download [ngrok](https://ngrok.com/docs/getting-started/) and setup account
        * `ngrok http https://localhost:6000`
        * Set `INTERNET_URL` equal to the ngrok forwarding address (should end in `.ngrok-free.app`) at the top of `hindsight_server/initialize_server.py`
    * Copy `hindsight_server/res/template_san.cnf` to `hindsight_server/res/san.cnf`
    * Fill in and replace the `${}` sections in `hindsight_server/res/san.cnf`
    * Run: `hindsight_server/initialize_server.py`

3) **Running**
    * For querying you may need to change the LLM and Embedding models in `hindsight_server/config.py` depending on your machine
    * It is recommended to run the server using `gunicorn` to improve the performance
        * `cd hindsight_server`
        * `gunicorn --certfile=$HOME/.hindsight_server/server.crt --keyfile=$HOME/.hindsight_server/server.key -w 4 -b 0.0.0.0:6000 run_server:app`
    * You can also run the server by just calling `hindsight_server/run_server.py`

### App
1) Open `hindsight_android` in Android Studio.
2) You should be good to run the app on your device!

## Features
Currently the app has 3 "working" functionalities.
1) **Screen Recording:** Toggle screen recording on or off.
2) **Server Upload:** Upload screenshots directly to your server.
* The screenshots timeline can be viewed and searched by running `python timeline_view.py`
3) **Query:** Run natural language queries against the text in your screenshots

## Developing
You can easily build applications on top of Hindsight.
To access the database you can use the functions within `hindsight_server/db.py`:
```python
from db import HindsightDB

db = HindsightDB()

frames_df = db.get_frames()

search_results = db.search(text="hindsight")
```

## Settings
* **User Activity Detection:** This setting is recommended as, depending on your phone usage, it can signifantly save battery life. The app will only take a screenshot if the user has been active since the last screenshot.
* **Screenshots Per Auto Upload** This setting determines how many screenshots taken in a row before the app automatically attempts to upload to the server. (Could add setting to disable)

## Permissions
* **Screen Broadcasting:** The App requires screen broadcasting each time recording is started. Ideally this is only needed if the phone is turned off or if the user intentionally stops recording (pausing is available as well). However, the app is very buggy so it may be required more often.
* **Accessibility Access:** In order to use the `Only Take Screenshot when User is Active` setting and for the screenshot to be saved with the name of the application running, Accessibility access is required. Unfortunetly, this is the only robust way I could find to introduce this functionality.

## Contributions
Feedback and contributions are welcome! Please reach out if you have ideas or want to help improve Hindsight.

## Considerations
* **Security:** Lots of security concerns so would love feedback in that area!
* **Battery Usage:** It uses around 2% of my new google pixel8's battery. Hopefully this can be reduced even more, and I'm very curious if battery life will be too big of a limitation for other phones.
* **iPhone:** Unfortunetly, this would not work on iPhone as the broadcast functionality would require user permission each time the phone screen turns off.
* **Testing:** This has only been tested on a Pixel 8 and M3 Mac