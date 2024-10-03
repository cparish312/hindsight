package com.connor.hindsight.utils

import android.content.Context
import android.content.SharedPreferences

object Preferences {
    private const val PREF_FILE_NAME = "Hindsight"
    lateinit var prefs: SharedPreferences

    const val screenrecordingenabled = "ScreenRecordingEnabled"
    const val locationtrackingenabled = "LocationTrackingEnabled"
    const val recordwhenactive = "RecordWhenActive"
    const val cameracaptureenabled = "CameraCaptureEnabled"
    const val screenshotsperautoupload = "ScreenshotsPerAutoUpload"
    const val apikey = "ApiKey"
    const val localurl = "LocalUrl"
    const val interneturl = "InternetUrl"
    const val lastsynctimestamp = "LastSyncTimestamp"

    fun init(context: Context) {
        prefs = context.getSharedPreferences(PREF_FILE_NAME, Context.MODE_PRIVATE)

        PYTHON_CONFIG_INSERT_HERE
    }
}