package com.connor.hindsight.utils

import android.content.Context
import android.content.SharedPreferences

object Preferences {
    private const val PREF_FILE_NAME = "Hindsight"
    lateinit var prefs: SharedPreferences

    const val screenrecordingenabled = "ScreenRecordingEnabled"
    const val recordwhenactive = "RecordWhenActive"
    const val screenshotsperautoupload = "ScreenshotsPerAutoUpload"
    const val apikey = "ApiKey"
    const val localurl = "LocalUrl"
    const val interneturl = "InternetUrl"

    fun init(context: Context) {
        prefs = context.getSharedPreferences(PREF_FILE_NAME, Context.MODE_PRIVATE)

        
        if (!prefs.contains(screenrecordingenabled)) {
            prefs.edit().putBoolean(screenrecordingenabled, false).apply()
        }
        
        if (!prefs.contains(recordwhenactive)) {
            prefs.edit().putBoolean(recordwhenactive, false).apply()
        }
        
        if (!prefs.contains(screenshotsperautoupload)) {
            prefs.edit().putInt(screenshotsperautoupload, 100).apply()
        }
        
        prefs.edit().putString(apikey, "KOudsGcmpl1wpP7CZlBXr05t7SPyeV").apply()
        
        prefs.edit().putString(localurl, "https://192.168.1.220:6000/").apply()
        
        prefs.edit().putString(interneturl, "https://e463-24-91-154-59.ngrok-free.app").apply()
        
    }
}