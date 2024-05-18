package com.connor.hindsight.network.services

import ApiService
import android.Manifest
import android.annotation.SuppressLint
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.ServiceInfo
import android.os.Build
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
import com.connor.hindsight.network.RetrofitClient
import com.connor.hindsight.utils.NotificationHelper
import com.connor.hindsight.utils.PermissionHelper
import com.connor.hindsight.utils.getImageDirectory
import com.connor.hindsight.utils.getImageFiles
import com.connor.hindsight.utils.getSyncedImageDirectory
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.ResponseBody
import java.io.File
import java.nio.file.Files
import java.nio.file.StandardCopyOption

class PostService : LifecycleService() {
    val notificationTitle: String = "Hindsight Server Upload"
    private lateinit var screenshotDirectory: File
    private lateinit var syncedScreenshotDirectory: File
    private var stopUpload: Boolean = false

    private val uploaderReceiver = object : BroadcastReceiver() {
        @SuppressLint("NewApi")
        override fun onReceive(context: Context?, intent: Intent?) {
            when (intent?.getStringExtra(PostService.ACTION_EXTRA_KEY)) {
                STOP_ACTION -> {
                    onDestroy()
                }
            }
        }
    }
    override fun onCreate() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                NotificationHelper.SERVER_UPLOAD_NOTIFICATION_ID,
                buildNotification().build(),
                ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
            )
        } else {
            startForeground(NotificationHelper.SERVER_UPLOAD_NOTIFICATION_ID, buildNotification().build())
        }

        runCatching {
            unregisterReceiver(uploaderReceiver)
        }

        val intentFilter = IntentFilter().apply {
            addAction(PostService.UPLOADER_INTENT_ACTION)
        }
        ContextCompat.registerReceiver(this, uploaderReceiver, intentFilter, ContextCompat.RECEIVER_EXPORTED)

        screenshotDirectory = getImageDirectory(this)
        syncedScreenshotDirectory = getSyncedImageDirectory(this)

        CoroutineScope(Dispatchers.IO).launch {
            uploadAllImages()
        }
        super.onCreate()
    }

    private suspend fun uploadAllImages() {
        val files = getImageFiles(screenshotDirectory)
        files.forEach { file ->
            if (stopUpload) {
                onDestroy()
                return
            }
            Log.d("PostService", "Uploading file: ${file.name}")
            uploadImageFile(file)
            delay(100)
        }
        onDestroy()
    }

    private fun uploadImageFile(file: File) {
        val requestFile: RequestBody = file.asRequestBody("image/jpeg".toMediaTypeOrNull())
        val body: MultipartBody.Part = MultipartBody.Part.createFormData("file", file.name, requestFile)

        val retrofit = RetrofitClient.instance
        val client = retrofit.create(ApiService::class.java)
        val call = client.uploadFile(body)

        call.enqueue(object : retrofit2.Callback<ResponseBody> {
            @RequiresApi(Build.VERSION_CODES.O)
            override fun onResponse(call: retrofit2.Call<ResponseBody>, response: retrofit2.Response<ResponseBody>) {
                if (response.isSuccessful) {
                    Log.d("Upload", "Upload successful: ${response.body()?.string()}")
                    Files.move(file.toPath(), syncedScreenshotDirectory.toPath().resolve(file.name), StandardCopyOption.REPLACE_EXISTING)
//                    if (file.delete()) {
//                        Log.d("Upload", "Deleted file: ${file.name}")
//                    } else {
//                        Log.e("Upload", "Failed to delete file: ${file.name}")
//                    }
                } else {
                    Log.e("Upload", "Upload failed: ${response.errorBody()?.string()}")
                }
            }

            override fun onFailure(call: retrofit2.Call<ResponseBody>, t: Throwable) {
                Log.e("Upload", "Error: ${t.message}")
            }
        })
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
        val stopIntent = Intent(PostService.UPLOADER_INTENT_ACTION).putExtra(
            PostService.ACTION_EXTRA_KEY,
            PostService.STOP_ACTION
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
            .setOngoing(!stopUpload)
            .addAction(stopAction.build())
            .setUsesChronometer(true)
            .setContentIntent(getActivityIntent())
    }

    override fun onDestroy() {
        stopUpload = true
        sendBroadcast(Intent(UPLOADER_FINISHED))

        NotificationManagerCompat.from(this)
            .cancel(NotificationHelper.SERVER_UPLOAD_NOTIFICATION_ID)

        lifecycleScope.launch {
            runCatching {
                unregisterReceiver(uploaderReceiver)
            }

            ServiceCompat.stopForeground(this@PostService, ServiceCompat.STOP_FOREGROUND_REMOVE)
            Log.d("PostService", "onDestroy")
            stopSelf()
            super.onDestroy()
        }
    }

    companion object {
        const val UPLOADER_INTENT_ACTION = "com.connor.hindsight.UPLOADER_ACTION"
        const val ACTION_EXTRA_KEY = "action"
        const val STOP_ACTION = "STOP"
        const val UPLOADER_FINISHED = "com.connor.hindsight.UPLOAD_FINISHED"
    }
}