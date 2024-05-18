package com.connor.hindsight.services

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.util.DisplayMetrics
import android.util.Log
import android.view.Display
import androidx.activity.result.ActivityResult
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import com.connor.hindsight.R
import com.connor.hindsight.enums.RecorderState
import com.connor.hindsight.obj.ImageResolution
import com.connor.hindsight.obj.UserActivityState
import com.connor.hindsight.utils.getImageDirectory
import com.connor.hindsight.utils.Preferences

class ScreenRecorderService : RecorderService() {
    override val notificationTitle: String
        get() = getString(R.string.recording_screen)

    private var virtualDisplay: VirtualDisplay? = null
    private var mediaProjection: MediaProjection? = null
    private var activityResult: ActivityResult? = null

    private lateinit var imageReader: ImageReader
    private var handler: Handler? = null
    private var imageCaptureRunnable: Runnable? = null

    private var recorderLoopStopped: Boolean = false
    private var actionSinceLastScreenshot: Boolean = true

    private var recordWhenActive: Boolean =  Preferences.prefs.getBoolean(Preferences.recordwhenactive, false)

    override val fgServiceType: Int?
        get() = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION
        } else {
            null
        }

    fun prepare(data: ActivityResult) {
        this.activityResult = data
        initMediaProjection()
    }

    private fun initMediaProjection() {
        val mProjectionManager = getSystemService(
            Context.MEDIA_PROJECTION_SERVICE
        ) as MediaProjectionManager
        try {
            mediaProjection = mProjectionManager.getMediaProjection(
                Activity.RESULT_OK,
                activityResult?.data!!
            )
        } catch (e: Exception) {
            Log.e("Media Projection Error", e.toString())
            onDestroy()
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            mediaProjection!!.registerCallback(object : MediaProjection.Callback() {
                override fun onStop() {
                    sendBroadcast(Intent(SCREEN_RECORDER_STOPPED))
                    onDestroy()
                }
            }, null)
        }
    }

    override fun start() {
        super.start()
        val resolution = getScreenResolution()
        val density = resolution.density
        val width = resolution.width
        val height = resolution.height
        Log.d("ScreenRecordingService", "Screen resolution: $width x $height x $density")

        mediaProjection?.let { mp ->
            imageReader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2)
            virtualDisplay = mp.createVirtualDisplay("ScreenRecordingService",
                width, height, density,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                imageReader.surface, object : VirtualDisplay.Callback() {
                    override fun onStopped() {
                        super.onStopped()
                        // Handle the virtual display being stopped
                        onDestroy()
                    }
                }, null)

            handler = Handler(Looper.getMainLooper())
            imageCaptureRunnable = object : Runnable {
                override fun run() {
                    if (recordWhenActive && !UserActivityState.userActive) {
                        Log.d("ScreenRecordingService", "Skipping Screenshot as User has been inactive")
                        postScreenshot(this)
                        return
                    }
                    val image = imageReader.acquireLatestImage()
                    Log.d("ScreenRecordingService", "Image Acquired")
                    image?.let {
                        val buffer = it.planes[0].buffer
                        val pixelStride = it.planes[0].pixelStride
                        val rowStride = it.planes[0].rowStride

                        val offset = (rowStride - pixelStride * width) / pixelStride
                        val w = width + offset
                        val bitmap = Bitmap.createBitmap(w, height, Bitmap.Config.ARGB_8888)
                        bitmap.copyPixelsFromBuffer(buffer)

                        saveImageData(bitmap, this@ScreenRecorderService)
                        it.close()
                    }
                    // Schedule the next capture
                    UserActivityState.userActive = false
                    postScreenshot(this)
                }
            }
            // Initial delay before starting the recurring task
            handler?.postDelayed(imageCaptureRunnable!!, 2000)  // Start after a delay of 2 seconds
        }
    }

    private fun postScreenshot(runnable: Runnable) {
        if (recorderState == RecorderState.ACTIVE){
            recorderLoopStopped = false
            handler?.postDelayed(runnable, 2000)
        }
        else {
            recorderLoopStopped = true
        }
    }

//    private fun saveImageData(bitmap: Bitmap, context: Context) {
//        val contentValues = ContentValues().apply {
//            put(MediaStore.MediaColumns.DISPLAY_NAME, "screenshot_${System.currentTimeMillis()}.jpg")
//            put(MediaStore.MediaColumns.MIME_TYPE, "image/jpeg")
//            put(MediaStore.MediaColumns.RELATIVE_PATH, "${Environment.DIRECTORY_PICTURES}/hindsight")
//        }
//
//        val uri = context.contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, contentValues)
//        uri?.let {
//            try {
//                context.contentResolver.openOutputStream(it)?.use { outputStream ->
//                    bitmap.compress(Bitmap.CompressFormat.JPEG, 100, outputStream)
//                    Log.d("ScreenRecordingService", "Image saved to $uri")
//                }
//            } catch (e: IOException) {
//                Log.e("ScreenRecordingService", "Failed to save image", e)
//            }
//        }
//    }

    private fun saveImageData(bitmap: Bitmap, context: Context) {
        // Use the app's private storage directory
        val directory = getImageDirectory(context)

        val file = File(directory, "screenshot_${System.currentTimeMillis()}.jpg")
        try {
            FileOutputStream(file).use { fos ->
                bitmap.compress(Bitmap.CompressFormat.JPEG, 100, fos)
                Log.d("ScreenRecordingService", "Image saved to ${file.absolutePath}")
            }
        } catch (e: IOException) {
            Log.e("ScreenRecordingService", "Failed to save image", e)
        }
    }

    private fun getScreenResolution(): ImageResolution {
        val displayManager = getSystemService(Context.DISPLAY_SERVICE) as DisplayManager
        val display = displayManager.getDisplay(Display.DEFAULT_DISPLAY)

        // TODO Use the window API instead on newer devices
        val metrics = DisplayMetrics()
        display.getRealMetrics(metrics)

        return ImageResolution(
            metrics.widthPixels,
            metrics.heightPixels,
            metrics.densityDpi,
            display.refreshRate.toInt()
        )
    }

    override fun onDestroy() {
        Log.d("ScreenRecordingService", "Destroying Screen Recording Service")
        handler?.removeCallbacks(imageCaptureRunnable!!)  // Stop the recurring image capture
        imageReader.close()
        virtualDisplay?.release()
        mediaProjection?.stop()  // This will trigger the callback's onStop method
        super.onDestroy()
    }

    override  fun resume(){
        super.resume()
        // recorderLoopStopped ensures that the previous image capture is stopped
        if (recorderState == RecorderState.ACTIVE && recorderLoopStopped){
            handler?.postDelayed(imageCaptureRunnable!!, 2000)
        }
    }

    companion object {
        const val SCREEN_RECORDER_STOPPED = "com.connor.hindsight.SCREEN_RECORDER_STOPPED"
    }
}
