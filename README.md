# Hindsight <img src="https://github.com/cparish312/hindsight/blob/main/assets/hindsight_icon.png" width="40">

Look back on your digital experience with Hindsight! (very alpha)

---

## Overview
Hindsight is an android app that takes a screenshot every 2 seconds. The server upload functionality allows a user to upload the screenshots to a server running on their personal computer.

### Demos
<a href="https://www.loom.com/share/669eecf3c04648d4aae1565ead56273f">
    <img style="max-width:300px;" src="https://cdn.loom.com/sessions/thumbnails/669eecf3c04648d4aae1565ead56273f-with-play.gif">
</a>
<a href="https://www.loom.com/share/8b3f6d4ed66d458c8b901ff5700563be">
    <img style="max-width:300px;" src="https://cdn.loom.com/sessions/thumbnails/8b3f6d4ed66d458c8b901ff5700563be-with-play.gif">
</a>

## Setup
### Server
1) **Conda Environment:**
    *   Install [conda](https://docs.anaconda.com/free/miniconda/miniconda-install/) if you don't have it already
    *   Create the conda environment: `conda env create -f hindsight_server_env_mac.yml`
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
    * Run: `bash start_server.sh`
        * This starts both the `server_backend.py` which just runs as a python process and the `run_server.py` which runs using `gunicorn` for better server performance.

### App
1) Open `hindsight_android` in Android Studio.
2) You should be good to run the app on your device!

### Changing Wifi
* Note when the computer wifi changes, querying should still work using ngrok, but in order to upload images again you will need to:
    1) Run: `python hindsight_server/initialize_server.py`
    2) Rebuild the app and install on your device

## Features
Currently the app has 4 "working" functionalities.
1) **Screen Recording:** Toggle screen recording on or off.
2) **Location Tracking:** Will save the last retrieved location every 2 seconds (if it has changed). Currently only works if screen recording is also enabled. Also be sure to give location tracking permissions.
3) **Server Upload:** Upload screenshots directly to your server.
* The screenshots timeline can be viewed and searched by running `python timeline_view.py`
4) **Query:** Run natural language queries against the text in your screenshots. There are 3 types of querying techniques currently available:
    1) Basic (Default or start query with `b/`): Uses top N contexts retreived by chromadb and feeds them to a single LLM call
    2) Long Context (start query with `l/`): For each top N contexts grabs the frames immediately before and after. For each context, the frames are combined and fed to an LLM. Finally, all of the results are fed to a summary LLM call to generate the response.
    3) Decomposition (start query with `d/`): First creates prompt asking LLM to generate prompts to gain context for the query. Then, it run Long Context on each of these sub-prompts. Finally, it combines all of the results of the sub-prompts and feeds it to the LLM with the user query.
    4) All (start query with `a/`): Runs all of the above methods and passes answers as a prompt asking to chose the best answer and report the method the answer came from.

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