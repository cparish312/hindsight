package com.connor.hindsight.network.services

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
import com.connor.hindsight.DB
import com.connor.hindsight.MainActivity
import com.connor.hindsight.R
import com.connor.hindsight.network.RetrofitClient
import com.connor.hindsight.network.interfaces.ApiService
import com.connor.hindsight.network.interfaces.SyncDBData
import com.connor.hindsight.obj.Content
import com.connor.hindsight.utils.NotificationHelper
import com.connor.hindsight.utils.ParsedContentResponse
import com.connor.hindsight.utils.Preferences
import com.connor.hindsight.utils.getImageDirectory
import com.connor.hindsight.utils.getImageFiles
import com.connor.hindsight.utils.getSyncedImageDirectory
import com.connor.hindsight.utils.parseJsonToContentResponse
import java.io.File
import java.io.IOException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.ResponseBody
import org.json.JSONArray
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class ServerUploadService : LifecycleService() {
    val notificationTitle: String = "Hindsight Server Upload"
    private lateinit var screenshotDirectory: File
    private lateinit var syncedScreenshotDirectory: File
    private var stopUpload: Boolean = false
    val lastSyncTimestamp = Preferences.prefs.getLong(Preferences.lastsynctimestamp, 0L)

    private val uploaderReceiver = object : BroadcastReceiver() {
        @SuppressLint("NewApi")
        override fun onReceive(context: Context?, intent: Intent?) {
            when (intent?.getStringExtra(ServerUploadService.ACTION_EXTRA_KEY)) {
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
            startForeground(
                NotificationHelper.SERVER_UPLOAD_NOTIFICATION_ID,
                buildNotification().build()
            )
        }
        
        isRunning = true

        runCatching {
            unregisterReceiver(uploaderReceiver)
        }

        val intentFilter = IntentFilter().apply {
            addAction(ServerUploadService.UPLOADER_INTENT_ACTION)
        }
        ContextCompat.registerReceiver(
            this,
            uploaderReceiver,
            intentFilter,
            ContextCompat.RECEIVER_EXPORTED
        )

        sendBroadcast(Intent(UPLOADER_STARTED))

        CoroutineScope(Dispatchers.IO).launch {
            syncDatabase()
        }

        CoroutineScope(Dispatchers.IO).launch {
            fetchNewContent()
        }

        screenshotDirectory = getImageDirectory(this)
        syncedScreenshotDirectory = getSyncedImageDirectory(this)

        CoroutineScope(Dispatchers.IO).launch {
            uploadAllImages()
        }
        super.onCreate()
    }

    private suspend fun getLastTimestamp(table: String): Int? {
        val serverUrl: String = Preferences.prefs.getString(
            Preferences.localurl,
            ""
        ).toString()
        val retrofit = RetrofitClient.getInstance(serverUrl, numTries = 3)
        val client = retrofit.create(ApiService::class.java)

        return try {
            val response = client.getLastTimestamp(table)
            if (response.isSuccessful) {
                response.body()?.last_timestamp?.toInt()
            } else {
                println("Failed to fetch the timestamp: ${response.errorBody()?.string()}")
                null
            }
        } catch (t: Throwable) {
            println("Error fetching timestamp: ${t.message}")
            null
        }
    }

    private suspend fun syncDatabase() {
        val dbHelper = DB(this@ServerUploadService)

        // val lastLocationsTimestamp = getLastTimestamp("locations")
        val syncLocationsCursor = dbHelper.getLocations(lastSyncTimestamp)
        val syncLocations = dbHelper.convertCursorToLocations(syncLocationsCursor)
        Log.d("ServerUploadService", "Sync locations: ${syncLocations.size}")

        // val lastAnnotationsTimestamp = getLastTimestamp("annotations")
        val syncAnnotationsCursor = dbHelper.getAnnotations(lastSyncTimestamp)
        val syncAnnotations = dbHelper.convertCursorToAnnotations(syncAnnotationsCursor)
        Log.d("ServerUploadService", "Sync annotations: ${syncAnnotations.size}")

        val syncContentCursor = dbHelper.getContent(lastSyncTimestamp)
        val syncContent = dbHelper.convertCursorToContent(syncContentCursor)
        Log.d("ServerUploadService", "Sync content: ${syncContent.size}")

        val serverUrl: String = Preferences.prefs.getString(
            Preferences.localurl,
            ""
        ).toString()
        val retrofit = RetrofitClient.getInstance(serverUrl, numTries = 3)
        val client = retrofit.create(ApiService::class.java)
        val syncData = SyncDBData(syncAnnotations, syncLocations, syncContent)

        try {
            val response = client.syncDB(syncData)
            if (response.isSuccessful) {
                Log.d("ServerUploadService", "DB Sync successful")
                val currentTimestamp = System.currentTimeMillis()
                Preferences.prefs.edit().putLong(Preferences.lastsynctimestamp, currentTimestamp).apply()
            } else {
                Log.e("ServerUploadService", "DB Sync failed: ${response.errorBody()?.string()}")
            }
        } catch (e: Exception) {
            Log.e("ServerUploadService", "Network call failed with exception: ${e.message}")
        }
    }

    private suspend fun fetchNewContent() {
        val dbHelper = DB(this@ServerUploadService)

        val serverUrl: String = Preferences.prefs.getString(
            Preferences.localurl,
            ""
        ).toString()
        val retrofit = RetrofitClient.getInstance(serverUrl, numTries = 3)
        val client = retrofit.create(ApiService::class.java)

        val maxContentId = dbHelper.getMaxContentId()

        try {
            // Fetch new content using the suspend function
            val responseBody = client.getNewContent(maxContentId, lastSyncTimestamp)

            // Process the response body if successful
            responseBody.use { response ->
                // Process the response body if successful
                val resultString = response.string()  // Convert ResponseBody to string
                val parsedResponse: ParsedContentResponse = parseJsonToContentResponse(resultString)

                // Add the new content to the database in a batch
                dbHelper.addContentBatch(parsedResponse.contentList)
                dbHelper.markContentAsViewed(parsedResponse.newlyViewedContentIds)
                Log.d("ServerUploadService", "Fetched new content: ${parsedResponse.contentList.size}")
            }
        } catch (e: Exception) {
            // Handle errors (network failure, etc.)
            Log.e("ServerUploadService", "Failed to fetch new content: ${e.message}")
        }
    }

    private suspend fun uploadAllImages() {
        val files = getImageFiles(screenshotDirectory)
        files.forEach { file ->
            if (stopUpload) {
                onDestroy()
                return
            }
            Log.d("ServerUploadService", "Uploading file: ${file.name}")
            uploadImageFile(file)
            delay(300)
        }
        onDestroy()
    }

    private fun uploadImageFile(file: File) {
        val requestFile: RequestBody = file.asRequestBody("image/jpeg".toMediaTypeOrNull())
        val body: MultipartBody.Part = MultipartBody.Part.createFormData(
            "file",
            file.name,
            requestFile
        )

        val serverUrl: String = Preferences.prefs.getString(
            Preferences.localurl,
            ""
        ).toString()
        val retrofit = RetrofitClient.getInstance(serverUrl, numTries = 3)
        val client = retrofit.create(ApiService::class.java)
        val call = client.uploadFile(body)

        call.enqueue(object : retrofit2.Callback<ResponseBody> {
            @RequiresApi(Build.VERSION_CODES.O)
            override fun onResponse(
                call: retrofit2.Call<ResponseBody>,
                response: retrofit2.Response<ResponseBody>
            ) {
                if (response.isSuccessful) {
                    Log.d("ServerUploadService", "Upload successful: ${response.body()?.string()}")
                    // Files.move(file.toPath(), syncedScreenshotDirectory.toPath().resolve(file.name), StandardCopyOption.REPLACE_EXISTING)
                    if (file.delete()) {
                        Log.d("Upload", "Deleted file: ${file.name}")
                    } else {
                        Log.e("Upload", "Failed to delete file: ${file.name}")
                    }
                } else {
                    Log.e("ServerUploadService", "Upload failed: ${response.errorBody()?.string()}")
                }
            }

            override fun onFailure(call: retrofit2.Call<ResponseBody>, t: Throwable) {
                if (t is IOException) {
                    Log.e("ServerUploadService", "Could not connect to server")
                    onDestroy()
                } else {
                    Log.e(
                        "ServerUploadService",
                        "Failure in response parsing or serialization: ${t.message}"
                    )
                }
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
        val stopIntent = Intent(ServerUploadService.UPLOADER_INTENT_ACTION).putExtra(
            ServerUploadService.ACTION_EXTRA_KEY,
            ServerUploadService.STOP_ACTION
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
        isRunning = false
        sendBroadcast(Intent(UPLOADER_FINISHED))

        NotificationManagerCompat.from(this)
            .cancel(NotificationHelper.SERVER_UPLOAD_NOTIFICATION_ID)

        lifecycleScope.launch {
            runCatching {
                unregisterReceiver(uploaderReceiver)
            }

            ServiceCompat.stopForeground(this@ServerUploadService, ServiceCompat.STOP_FOREGROUND_REMOVE)
            Log.d("ServerUploadService", "onDestroy")
            stopSelf()
            super.onDestroy()
        }
    }

    companion object {
        const val UPLOADER_INTENT_ACTION = "com.connor.hindsight.UPLOADER_ACTION"
        const val ACTION_EXTRA_KEY = "action"
        const val STOP_ACTION = "STOP"
        const val UPLOADER_FINISHED = "com.connor.hindsight.UPLOAD_FINISHED"
        const val UPLOADER_STARTED = "com.connor.hindsight.UPLOAD_STARTED"
        var isRunning = false
    }
}
