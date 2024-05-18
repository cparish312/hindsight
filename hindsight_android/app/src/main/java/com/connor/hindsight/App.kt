package com.connor.hindsight

import android.app.Application
import com.connor.hindsight.utils.NotificationHelper
import com.connor.hindsight.utils.Preferences

class App : Application() {
    override fun onCreate() {
        super.onCreate()
        Preferences.init(this)
        // NotificationHelper.buildNotificationChannels(this)
    }
}
