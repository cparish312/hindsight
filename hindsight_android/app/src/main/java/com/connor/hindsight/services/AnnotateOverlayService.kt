package com.connor.hindsight.services

import android.annotation.SuppressLint
import android.app.PendingIntent
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.ServiceInfo
import android.graphics.PixelFormat
import android.os.Build
import android.os.IBinder
import android.text.Editable
import android.text.TextWatcher
import android.util.Log
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.WindowManager
import android.widget.Button
import android.widget.EditText
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import com.connor.hindsight.DB
import com.connor.hindsight.MainActivity
import com.connor.hindsight.R
import com.connor.hindsight.utils.NotificationHelper

class AnnotateOverlayService : Service() {
    val notificationTitle: String = "Hindsight Annotate"
    private lateinit var windowManager: WindowManager
    private var overlayView: View? = null
    private lateinit var params: WindowManager.LayoutParams

    private val annotateOverlayReceiver = object : BroadcastReceiver() {
        @SuppressLint("NewApi")
        override fun onReceive(context: Context?, intent: Intent?) {
            when (intent?.getStringExtra(ACTION_EXTRA_KEY)) {
                STOP_ACTION -> {
                    onDestroy()
                }
            }
        }
    }

    override fun onBind(intent: Intent?): IBinder? {
        return null
    }

    override fun onCreate() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                NotificationHelper.ANNOTATE_OVERLAY_NOTIFICATION_ID,
                buildNotification().build(),
                ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
            )
        } else {
            startForeground(
                NotificationHelper.ANNOTATE_OVERLAY_NOTIFICATION_ID,
                buildNotification().build()
            )
        }

        super.onCreate()
        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        val inflater = getSystemService(LAYOUT_INFLATER_SERVICE) as LayoutInflater
        overlayView = inflater.inflate(R.layout.annotate_bubble_layout, null)

        params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
        PixelFormat.TRANSLUCENT
        )

        runCatching {
            unregisterReceiver(annotateOverlayReceiver)
        }

        val intentFilter = IntentFilter().apply {
            addAction(ANNOTATE_OVERLAP_ACTION)
        }
        ContextCompat.registerReceiver(
            this,
            annotateOverlayReceiver,
            intentFilter,
            ContextCompat.RECEIVER_EXPORTED
        )

        params.gravity = Gravity.TOP or Gravity.START
        params.softInputMode = WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE

        windowManager.addView(overlayView, params)

        val editTextBubble = overlayView?.findViewById<EditText>(R.id.editTextBubble)
        val buttonSubmit = overlayView?.findViewById<Button>(R.id.buttonSubmit)

        editTextBubble?.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                params.height = WindowManager.LayoutParams.WRAP_CONTENT
                windowManager.updateViewLayout(overlayView, params)
            }
            override fun afterTextChanged(s: Editable?) {}
        })

        buttonSubmit?.setOnClickListener {
            val text = editTextBubble?.text.toString()
            Log.d("AnnotateOverlayService", "Submit Button Clicked with text: $text")
            if (text.isNotEmpty()) {
                val dbHelper = DB(this@AnnotateOverlayService)
                dbHelper.addAnnotation(text)
                editTextBubble?.setText("")  // Clear the text after submission
            }
            onDestroy()
        }

        editTextBubble?.requestFocus()
    }

    override fun onDestroy() {
        super.onDestroy()
        overlayView?.let {
            windowManager.removeView(it)
            overlayView = null
        }

        NotificationManagerCompat.from(this)
            .cancel(NotificationHelper.ANNOTATE_OVERLAY_NOTIFICATION_ID)

        runCatching {
            unregisterReceiver(annotateOverlayReceiver)
        }

        ServiceCompat.stopForeground(this@AnnotateOverlayService, ServiceCompat.STOP_FOREGROUND_REMOVE)
        Log.d("AnnotateOverlayService", "onDestroy")
        stopSelf()
        super.onDestroy()
    }

    private fun getPendingIntent(intent: Intent, requestCode: Int): PendingIntent =
        PendingIntent.getBroadcast(
            this,
            requestCode,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

    private fun getActivityIntent(): PendingIntent {
        return PendingIntent.getActivity(
            this,
            6,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )
    }

    private fun buildNotification(): NotificationCompat.Builder {
        val stopIntent = Intent(ANNOTATE_OVERLAP_ACTION).putExtra(
            ACTION_EXTRA_KEY,
            STOP_ACTION
        )
        val stopAction = NotificationCompat.Action.Builder(
            null,
            getString(R.string.stop),
            getPendingIntent(stopIntent, 2)
        )

        return NotificationCompat.Builder(
            this,
            NotificationHelper.RECORDING_NOTIFICATION_CHANNEL
        )
            .setContentTitle(notificationTitle)
            .setSmallIcon(R.drawable.ic_notification)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setSilent(true)
            .addAction(stopAction.build())
            .setUsesChronometer(true)
            .setContentIntent(getActivityIntent())
    }

    companion object {
        const val ANNOTATE_OVERLAP_ACTION = "com.connor.hindsight.ANNOTATE_OVERLAY_ACTION"
        const val ACTION_EXTRA_KEY = "action"
        const val STOP_ACTION = "STOP"
    }
}
