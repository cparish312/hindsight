package com.connor.hindsight.services

import android.Manifest
import android.annotation.SuppressLint
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.media.MediaRecorder
import android.os.Binder
import android.os.Build
import android.os.IBinder
import android.os.ParcelFileDescriptor
import android.util.Log
import androidx.annotation.RequiresApi
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleService
import androidx.lifecycle.lifecycleScope
import com.connor.hindsight.MainActivity
import com.connor.hindsight.R
import com.connor.hindsight.enums.RecorderState
import com.connor.hindsight.network.services.ServerUploadService
import com.connor.hindsight.utils.NotificationHelper
import com.connor.hindsight.utils.PermissionHelper
import com.connor.hindsight.utils.Preferences
import com.connor.hindsight.utils.ServerConnectionCallback
import com.connor.hindsight.utils.checkServerConnection
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

abstract class RecorderService : LifecycleService() {
    abstract val notificationTitle: String

    private val binder = LocalBinder()
    var recorder: MediaRecorder? = null
    var fileDescriptor: ParcelFileDescriptor? = null

    var onRecorderStateChanged: (RecorderState) -> Unit = {}
    open val fgServiceType: Int? = null
    var recorderState: RecorderState = RecorderState.IDLE

    private val recorderReceiver = object : BroadcastReceiver() {
        @SuppressLint("NewApi")
        override fun onReceive(context: Context?, intent: Intent?) {
            when (intent?.getStringExtra(ACTION_EXTRA_KEY)) {
                STOP_ACTION -> onDestroy()
                PAUSE_RESUME_ACTION -> {
                    if (recorderState == RecorderState.ACTIVE) pause() else resume()
                }
            }
            when (intent?.action) {
                Intent.ACTION_SCREEN_OFF -> {
                    pause()
                }
                Intent.ACTION_SCREEN_ON -> {
                    resume()
                }
            }
        }
    }

    override fun onBind(intent: Intent): IBinder? {
        super.onBind(intent)
        return binder
    }

    inner class LocalBinder : Binder() {
        // Return this instance of [BackgroundMode] so clients can call public methods
        fun getService(): RecorderService = this@RecorderService
    }

    override fun onCreate() {
        val notification = buildNotification()
        if (fgServiceType != null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                NotificationHelper.RECORDING_NOTIFICATION_ID,
                notification.build(),
                fgServiceType!!
            )
        } else {
            startForeground(NotificationHelper.RECORDING_NOTIFICATION_ID, notification.build())
        }

        runCatching {
            unregisterReceiver(recorderReceiver)
        }
        val intentFilter = IntentFilter().apply {
            addAction(RECORDER_INTENT_ACTION)
            addAction(Intent.ACTION_SCREEN_OFF)
            addAction(Intent.ACTION_SCREEN_ON)
        }
        ContextCompat.registerReceiver(
            this,
            recorderReceiver,
            intentFilter,
            ContextCompat.RECEIVER_EXPORTED
        )

        super.onCreate()
    }

    private fun buildNotification(): NotificationCompat.Builder {
        val stopIntent = Intent(RECORDER_INTENT_ACTION).putExtra(ACTION_EXTRA_KEY, STOP_ACTION)
            .putExtra(
                FROM_RECORDER_SERVICE,
                true
            )
        val stopAction = NotificationCompat.Action.Builder(
            null,
            getString(R.string.stop),
            getPendingIntent(stopIntent, 2)
        )

        val resumeOrPauseIntent = Intent(RECORDER_INTENT_ACTION).putExtra(
            ACTION_EXTRA_KEY,
            PAUSE_RESUME_ACTION
        ).putExtra(
            FROM_RECORDER_SERVICE,
            true
        )
        val resumeOrPauseAction = NotificationCompat.Action.Builder(
            null,
            if (recorderState == RecorderState.ACTIVE) {
                getString(R.string.pause)
            } else {
                getString(R.string.resume)
            },
            getPendingIntent(resumeOrPauseIntent, 3)
        )

        return NotificationCompat.Builder(
            this,
            NotificationHelper.RECORDING_NOTIFICATION_CHANNEL
        )
            .setContentTitle(notificationTitle)
            .setSmallIcon(R.drawable.ic_notification)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setSilent(true)
            .setOngoing(recorderState == RecorderState.ACTIVE)
            .addAction(stopAction.build())
            .apply {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                    addAction(
                        resumeOrPauseAction.build()
                    )
                }
            }
            .setUsesChronometer(true)
            .setContentIntent(getActivityIntent())
    }

    @SuppressLint("MissingPermission")
    fun updateNotification() {
        if (!PermissionHelper.hasPermission(this, Manifest.permission.POST_NOTIFICATIONS)) {
            return
        }
        val notification = buildNotification().build()
        NotificationManagerCompat.from(this).notify(
            NotificationHelper.RECORDING_NOTIFICATION_ID,
            notification
        )
    }

    private fun getPendingIntent(intent: Intent, requestCode: Int): PendingIntent =
        PendingIntent.getBroadcast(
            this,
            requestCode,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

    open fun start() {
        runCatching {
            recorderState = RecorderState.ACTIVE
            onRecorderStateChanged(recorderState)
        }
        updateNotification()
    }

    @RequiresApi(Build.VERSION_CODES.N)
    open fun pause() {
        Log.d("ScreenRecordingService", "Recorder paused")
        recorder?.pause()
        runCatching {
            recorderState = RecorderState.PAUSED
            onRecorderStateChanged(recorderState)
        }
        updateNotification()
    }

    @RequiresApi(Build.VERSION_CODES.N)
    open fun resume() {
        recorder?.resume()
        runCatching {
            recorderState = RecorderState.ACTIVE
            onRecorderStateChanged(recorderState)
        }
        updateNotification()
    }

    override fun onDestroy() {
        runCatching {
            recorderState = RecorderState.IDLE
            onRecorderStateChanged(recorderState)
        }

        NotificationManagerCompat.from(this)
            .cancel(NotificationHelper.RECORDING_NOTIFICATION_ID)

        lifecycleScope.launch {
            withContext(Dispatchers.IO) {
                recorder?.runCatching {
                    stop()
                    release()
                }
                recorder = null
                fileDescriptor?.close()
            }

            runCatching {
                unregisterReceiver(recorderReceiver)
            }

            ServiceCompat.stopForeground(
                this@RecorderService,
                ServiceCompat.STOP_FOREGROUND_REMOVE
            )
            stopSelf()

            super.onDestroy()
        }
    }

    private fun getActivityIntent(): PendingIntent {
        Log.d("ScreenRecordingService", "Starting Main Activity from notification")
        val intent = Intent(this, MainActivity::class.java).putExtra(FROM_RECORDER_SERVICE, true)
        return PendingIntent.getActivity(
            this,
            6,
            intent,
            PendingIntent.FLAG_IMMUTABLE
        )
    }

    fun uploadToServer() {
        Log.d("RecorderService", "uploadToServer")
        val primaryUrl: String = Preferences.prefs.getString(
            Preferences.localurl,
            ""
        ).toString()
        checkServerConnection(serverUrl = primaryUrl, object : ServerConnectionCallback {
            override fun onServerStatusChecked(isConnected: Boolean) {
                if (isConnected) {
                    Log.d(
                        "RecorderService",
                        "Connection successful, proceeding with service initialization."
                    )
                    val uploadIntent = Intent(this@RecorderService, ServerUploadService::class.java)
                    ContextCompat.startForegroundService(this@RecorderService, uploadIntent)
                } else {
                    Log.e("RecorderService", "No server connection, aborting upload.")
                }
            }
        })
    }

    companion object {
        const val RECORDER_INTENT_ACTION = "com.connor.hindsight.RECORDER_ACTION"
        const val ACTION_EXTRA_KEY = "action"
        const val STOP_ACTION = "STOP"
        const val PAUSE_RESUME_ACTION = "PR"
        const val FROM_RECORDER_SERVICE = "com.connor.hindsight.FROM_RECORDER_SERVICE"
    }
}
