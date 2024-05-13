package com.connor.hindsight.receivers

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationManagerCompat
import com.connor.hindsight.App
import com.connor.hindsight.services.RecorderService
import com.connor.hindsight.utils.IntentHelper
import com.connor.hindsight.utils.NotificationHelper

class FinishedNotificationReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val fileName = intent.getStringExtra(RecorderService.FILE_NAME_EXTRA_KEY) ?: return
        val file = (context.applicationContext as App).fileRepository
            .getOutputDir().findFile(fileName)

        when (intent.getStringExtra(RecorderService.ACTION_EXTRA_KEY)) {
            RecorderService.SHARE_ACTION -> file?.let { IntentHelper.shareFile(context, it) }
            RecorderService.DELETE_ACTION -> file?.delete()
        }
        NotificationManagerCompat.from(context)
            .cancel(NotificationHelper.RECORDING_FINISHED_N_ID)
    }
}
