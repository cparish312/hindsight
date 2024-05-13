package com.connor.hindsight.services

import android.app.Service
import android.app.Activity
import android.content.Intent
import android.os.IBinder
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.ContentValues
import android.os.Build
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.media.ImageReader
import android.graphics.PixelFormat
import android.hardware.display.VirtualDisplay
import android.hardware.display.DisplayManager
import android.os.Handler
import android.os.Looper
import android.content.Context
import android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION
import android.provider.MediaStore
import android.util.Log
import androidx.annotation.RequiresApi
import com.connor.hindsight.utils.Constants
import java.io.IOException

class ScreenRecordingService_o : Service() {
    companion object {
        const val FOREGROUND_SERVICE_ID = 1
        const val CHANNEL_ID = "screen_recording_channel"
        const val CHANNEL_NAME = "Screen Recording Service"
        const val NOTIFICATION_TITLE = "Screen Recording"
        const val NOTIFICATION_TEXT = "Recording is running..."
    }

    private var mediaProjection: MediaProjection? = null
    private var virtualDisplay: VirtualDisplay? = null
    private lateinit var imageReader: ImageReader
    private var handler: Handler? = null
    private var imageCaptureRunnable: Runnable? = null

    @RequiresApi(Build.VERSION_CODES.TIRAMISU)
    override fun onStartCommand(intent: Intent, flags: Int, startId: Int): Int {
        when (intent.action) {
            Constants.ACTION_START_SCREEN_CAPTURE -> startScreenCapture(intent)
            Constants.ACTION_STOP_SCREEN_CAPTURE -> stopScreenCapture()
        }
        return START_NOT_STICKY
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    @RequiresApi(Build.VERSION_CODES.TIRAMISU)
    private fun startScreenCapture(intent: Intent) {
        val resultCode = intent.getIntExtra("resultCode", Activity.RESULT_CANCELED)
        val dataIntent = intent.getParcelableExtra("dataIntent", Intent::class.java)

        Log.d("ScreenRecordingService", "Started")
        if (dataIntent != null && resultCode == Activity.RESULT_OK) {
            Log.d("ScreenRecordingService", "Starting Recording")
            startForeground(FOREGROUND_SERVICE_ID, createNotification(), FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION)
            initializeMediaProjection(resultCode, dataIntent)
            startRecording()
        }
    }

    private fun initializeMediaProjection(resultCode: Int, data: Intent) {
        val mediaProjectionManager = getSystemService(MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        mediaProjection = mediaProjectionManager.getMediaProjection(resultCode, data)

        mediaProjection?.registerCallback(object : MediaProjection.Callback() {
            override fun onStop() {
                super.onStop()
                // Handle what happens when media projection is stopped
                stopScreenCapture()
                // Clean up resources, etc.
                mediaProjection?.unregisterCallback(this)
            }
        }, null)
    }

    private fun startRecording() {
        mediaProjection?.let { mp ->
            val metrics = resources.displayMetrics
            val density = metrics.densityDpi
            val width = metrics.widthPixels
            val height = metrics.heightPixels

            imageReader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2)
            virtualDisplay = mp.createVirtualDisplay("ScreenRecordingService",
                width, height, density,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                imageReader.surface, object : VirtualDisplay.Callback() {
                    override fun onStopped() {
                        super.onStopped()
                        // Handle the virtual display being stopped
                        stopScreenCapture()
                    }
                }, null)

            handler = Handler(Looper.getMainLooper())
            imageCaptureRunnable = object : Runnable {
                override fun run() {
                    val image = imageReader.acquireLatestImage()
                    if (image != null && image.format == PixelFormat.RGBA_8888) {
                        Log.e("ScreenRecordingService", "Image is valid")
                    } else {
                        Log.e("ScreenRecordingService", "Invalid image or format")
                    }
                    image?.let {
                        Log.d("ScreenRecordingService", "Image format: ${image.format}")
                        val buffer = it.planes[0].buffer
                        val capacity = buffer.capacity()  // Total capacity of the buffer
                        val remaining = buffer.remaining()  // Remaining data in the buffer
                        Log.d("ScreenRecordingService", "Buffer capacity: $capacity, Remaining: $remaining")
                        val data = ByteArray(buffer.capacity())
                        val expectedSize = width * height * 4  // For RGBA_8888, each pixel uses 4 bytes.
                        if (data.size == expectedSize) {
                            Log.d("ScreenRecordingService", "Data array size is correct: ${data.size} bytes")
                        } else {
                            Log.e("ScreenRecordingService", "Data array size is incorrect: ${data.size} bytes, expected: $expectedSize")
                        }
                        if (data.isNotEmpty()) {
                            Log.d("ScreenRecordingService", "Sample byte values: ${data.take(10).joinToString(", ")}")
                        }
                        if (data.none { it != 0.toByte() }) {
                            Log.e("ScreenRecordingService", "Buffer contains only zeros")
                        }

                        buffer.rewind()
                        buffer.get(data)
                        saveImageData(data, this@ScreenRecordingService_o)
                        it.close()
                    }
                    // Schedule the next capture
                    handler?.postDelayed(this, 2000)
                }
            }
            // Initial delay before starting the recurring task
            handler?.postDelayed(imageCaptureRunnable!!, 2000)  // Start after a delay of 2 seconds
        }
    }

    private fun saveImageData(data: ByteArray, context: Context) {
        val resolver = context.contentResolver
        val contentValues = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, "screenshot_${System.currentTimeMillis()}.jpg")
            put(MediaStore.MediaColumns.MIME_TYPE, "image/jpeg")
            put(MediaStore.MediaColumns.RELATIVE_PATH, "Pictures/hindsight")  // Save images in the Pictures/hindsight directory
        }

        val uri = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, contentValues)
        uri?.let {
            try {
                resolver.openOutputStream(uri)?.use { outputStream ->
                    outputStream.write(data)
                    outputStream.flush()
                }
                Log.d("ScreenRecordingService", "Image saved to $uri")
                val fileSize = contentResolver.openInputStream(uri)?.use { inputStream ->
                    inputStream.available()
                }
                Log.d("ScreenRecordingService", "File size: $fileSize bytes")

                contentResolver.openInputStream(uri)?.use { inputStream ->
                    val size = inputStream.available()  // Check the available data size
                    Log.d("ScreenRecordingService", "Read file size: $size bytes")
                }

            } catch (e: IOException) {
                Log.e("ScreenRecordingService", "Failed to save image", e)
            }
        }
    }

    override fun onBind(intent: Intent?): IBinder? {
        return null
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Notifications for ongoing screen recording"
            }
            val notificationManager: NotificationManager =
                getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }

    @RequiresApi(Build.VERSION_CODES.O)
    private fun createNotification(): Notification {
        return Notification.Builder(this, CHANNEL_ID)
            .setContentTitle(NOTIFICATION_TITLE)
            .setContentText(NOTIFICATION_TEXT)
            // .setSmallIcon(R.drawable.ic_notification) // Make sure to define a notification icon in your drawable resources
            .build()
    }

    private fun stopScreenCapture() {
        Log.d("ScreenRecordingService", "Stopping Screen Recording Service")
        handler?.removeCallbacks(imageCaptureRunnable!!)  // Stop the recurring image capture
        imageReader.close()
        virtualDisplay?.release()
        mediaProjection?.stop()  // This will trigger the callback's onStop method
    }
}
