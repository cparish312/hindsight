package com.connor.hindsight.utils

import android.content.Context
import android.content.SharedPreferences

object Preferences {
    private const val PREF_FILE_NAME = "Hindsight"
    lateinit var prefs: SharedPreferences

    const val screenrecordingenabled = "ScreenRecordingEnabled"
    const val recordwhenactive = "RecordWhenActive"

    fun init(context: Context) {
        prefs = context.getSharedPreferences(PREF_FILE_NAME, Context.MODE_PRIVATE)

        if (!prefs.contains(screenrecordingenabled)) {
            prefs.edit().putBoolean(screenrecordingenabled, false).apply()
        }
        if (!prefs.contains(recordwhenactive)) {
            prefs.edit().putBoolean(recordwhenactive, true).apply()
        }
    }
}
