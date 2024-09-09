### Server
1) **Conda Environment:**
    *   Install [conda](https://docs.anaconda.com/free/miniconda/miniconda-install/) if you don't have it already
    *   Create the conda environment: `conda env create -f hindsight_server_env_mac.yml`
    *   Activate the env using: `conda activate hindsight_server`
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
        * This starts both the `server_backend.py` which just runs as a python process and the `run_server.py` which runs as a WSGI server using Flask and Gevent.

### App
1) Open `hindsight_android` in Android Studio.
2) You should be good to run the app on your device!

### Changing Wifi
* Note when the computer wifi changes, querying should still work using ngrok, but in order to upload images again you will need to:
    1) Run: `python hindsight_server/initialize_server.py`
    2) Rebuild the app and install on your device