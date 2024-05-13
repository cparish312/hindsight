package com.connor.hindsight

import android.app.Application
import com.connor.hindsight.utils.FileRepository
import com.connor.hindsight.utils.FileRepositoryImpl
import com.connor.hindsight.utils.NotificationHelper
import com.connor.hindsight.utils.Preferences

class App : Application() {
    val fileRepository: FileRepository by lazy {
        FileRepositoryImpl(this)
    }
    override fun onCreate() {
        super.onCreate()
        Preferences.init(this)
        NotificationHelper.buildNotificationChannels(this)
    }
}
