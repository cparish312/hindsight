package com.connor.hindsight.models

import android.Manifest
import android.annotation.SuppressLint
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.ServiceConnection
import android.os.Build
import android.os.IBinder
import android.util.Log
import android.widget.Toast
import androidx.activity.result.ActivityResult
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.content.ContextCompat
import androidx.lifecycle.ViewModel
import com.connor.hindsight.R
import com.connor.hindsight.enums.RecorderState
import com.connor.hindsight.services.RecorderService
import com.connor.hindsight.services.ScreenRecorderService
import com.connor.hindsight.utils.PermissionHelper

class RecorderModel : ViewModel() {
    var recorderState by mutableStateOf(RecorderState.IDLE)
    var recordedTime by mutableStateOf<Long?>(null)
    private var activityResult: ActivityResult? = null

    @SuppressLint("StaticFieldLeak")
    private var recorderService: RecorderService? = null

    private val connection = object : ServiceConnection {
        override fun onServiceConnected(className: ComponentName, service: IBinder) {
            Log.d("RecorderModel", "Connection onServiceConnected")
            recorderService = (service as RecorderService.LocalBinder).getService()
            recorderService?.onRecorderStateChanged = {
                recorderState = it
            }
            (recorderService as? ScreenRecorderService)?.prepare(activityResult!!)
            recorderService?.start()
        }

        override fun onServiceDisconnected(arg0: ComponentName) {
            recorderService = null
        }
    }

    fun startVideoRecorder(context: Context, result: ActivityResult) {
        activityResult = result
        val serviceIntent = Intent(context, ScreenRecorderService::class.java)
        startRecorderService(context, serviceIntent)
    }

    private fun startRecorderService(context: Context, intent: Intent) {
        runCatching {
            context.unbindService(connection)
        }

        listOfNotNull(
            ScreenRecorderService::class.java,
        ).forEach {
            runCatching {
                context.stopService(Intent(context, it))
            }
        }
        ContextCompat.startForegroundService(context, intent)
        context.bindService(intent, connection, Context.BIND_AUTO_CREATE)

        Log.d("RecorderModel", "Start Recorder Service")
    }

    fun stopRecording() {
        recorderService?.onDestroy()
        recordedTime = null
    }

    @SuppressLint("NewApi")
    fun hasScreenRecordingPermissions(context: Context): Boolean {
        val requiredPermissions = arrayListOf<String>()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            requiredPermissions.add(Manifest.permission.POST_NOTIFICATIONS)
        }

        if (requiredPermissions.isEmpty()) return true

        val granted = PermissionHelper.checkPermissions(context, requiredPermissions.toTypedArray())
        if (!granted) {
            Toast.makeText(
                context,
                context.getString(R.string.no_sufficient_permissions), Toast.LENGTH_SHORT
            )
                .show()
        }
        return granted
    }
}