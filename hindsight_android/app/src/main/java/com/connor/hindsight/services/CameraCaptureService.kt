package com.connor.hindsight.services

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageFormat
import android.hardware.camera2.CameraAccessException
import android.hardware.camera2.CameraCaptureSession
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraDevice
import android.hardware.camera2.CameraManager
import android.hardware.camera2.CameraMetadata
import android.hardware.camera2.CaptureRequest
import android.media.ImageReader
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.Surface
import androidx.core.app.ActivityCompat
import androidx.lifecycle.LifecycleService
import com.connor.hindsight.utils.getImageDirectory
import java.io.File
import java.io.FileOutputStream
import java.io.IOException

class CameraCaptureService : LifecycleService() {
    private var handler: Handler? = null
    // private var imageReader: ImageReader? = null

    private var cameraDevice: CameraDevice? = null // Make global var to ensure cleaner closing
    private var pendingCaptures = 2

    override fun onCreate() {
        Log.d("CameraCaptureService", "onCreate")
        handler = Handler(Looper.getMainLooper())
        takePictureFromBothCameras()
        super.onCreate()
    }

    fun takePictureFromBothCameras() {
        // Initialize the camera manager and get camera characteristics
        Thread.sleep(1000)
        setUpImageReader("0", "backCamera")
//        val cameraManager = getSystemService(Context.CAMERA_SERVICE) as CameraManager
//        val characteristics = cameraManager.getCameraCharacteristics("0")

        // for (cameraId in cameraManager.cameraIdList) {
//        for (cameraId in listOf("0", "1")) {
//            val characteristics = cameraManager.getCameraCharacteristics(cameraId)
//            val cameraDirection = characteristics.get(CameraCharacteristics.LENS_FACING)
//            if (cameraDirection != null) {
//                if (cameraDirection == CameraCharacteristics.LENS_FACING_BACK) {
//                    setUpImageReader(cameraId, "backCamera" )
//                }
//                if (cameraDirection == CameraCharacteristics.LENS_FACING_FRONT) {
//                    setUpImageReader(cameraId, "frontCamera")
//                }
//                Thread.sleep(5000)
//            }
//        }
    }
    fun setUpImageReader(cameraId: String, cameraName: String) {
//        imageReader?.close()
        cameraDevice?.close()
        Log.d("CameraCaptureService", "Setting up image reader for $cameraName")
        val cameraManager = getSystemService(Context.CAMERA_SERVICE) as CameraManager
        val characteristics = cameraManager.getCameraCharacteristics(cameraId)
        val map = characteristics.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP)!!
        val outputSize = map.getOutputSizes(ImageFormat.JPEG).maxByOrNull { it.width * it.height }!!
        Log.d("CameraCaptureService", "Output size for $cameraName: ${outputSize.width}x${outputSize.height}")

        // Create an ImageReader holding the maximum available size.
        val imageReader = ImageReader.newInstance(outputSize.width, outputSize.height, ImageFormat.JPEG, 2).apply {
            setOnImageAvailableListener({ reader ->
                Log.d("CameraCaptureService", "Image Available for $cameraName")
                val image = reader.acquireNextImage()
                val buffer = image.planes[0].buffer
                val bytes = ByteArray(buffer.remaining())
                buffer.get(bytes)
                val bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                Log.d("CameraCaptureService", "Image Acquired for $cameraName")
                saveImageData(bitmap, this@CameraCaptureService, cameraName)
                image.close()
                if (cameraName == "backCamera") {
                    setUpImageReader("1", "frontCamera" )
                } else{
                    onDestroy()
                }
                checkAndFinalize()
            }, null)
        }

        openCameraSafely(handler!!, this, cameraId, imageReader!!.surface)
    }

    fun createCameraCaptureSession(cameraDevice: CameraDevice, captureSurface: Surface) {
        Log.d("CameraCaptureSession", "Creating camera capture session")
        cameraDevice.createCaptureSession(listOf(captureSurface), object : CameraCaptureSession.StateCallback() {
            override fun onConfigured(session: CameraCaptureSession) {
                val captureRequestBuilder = cameraDevice.createCaptureRequest(CameraDevice.TEMPLATE_STILL_CAPTURE).apply {
                    addTarget(captureSurface)
                    set(CaptureRequest.CONTROL_MODE, CameraMetadata.CONTROL_MODE_AUTO)
                }
                try {
                    session.capture(captureRequestBuilder.build(), null, null)
                    Log.d("CameraCaptureSession", "Camera capture session configured")
                } catch (e: CameraAccessException) {
                    Log.e("CameraCaptureSession", "Failed to capture image", e)
                    e.printStackTrace()
                    cameraDevice.close()
                }
            }

            override fun onConfigureFailed(session: CameraCaptureSession) {
                // Handle failure
            }
        }, null)
    }
    fun openCamera(context: Context, cameraId: String, captureSurface: Surface) {
        val cameraManager = context.getSystemService(Context.CAMERA_SERVICE) as CameraManager
        try {
            if (ActivityCompat.checkSelfPermission(context, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
                Log.e("CameraPermission", "Camera permission not granted")
                return
            }

            cameraManager.openCamera(cameraId, object : CameraDevice.StateCallback() {
                override fun onOpened(cd: CameraDevice) {
                    Log.d("CameraAccess", "Camera opened successfully")
                    try {
                        cameraDevice = cd
                        createCameraCaptureSession(cameraDevice!!, captureSurface)
                    } catch (e: Exception) {
                        Log.e("CameraAccess", "Failed to handle camera properly", e)
                    }
                }

                override fun onDisconnected(cd: CameraDevice) {
                    cameraDevice?.close()
                }

                override fun onError(cd: CameraDevice, error: Int) {
                    cameraDevice?.close()
                }
            }, null)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    fun openCameraSafely(handler: Handler, context: Context, cameraId: String, captureSurface: Surface) {
        try {
            openCamera(context, cameraId, captureSurface)
        } catch (e: CameraAccessException) {
            Log.e("CameraAccess", "Camera access error", e)
            if (e.reason == CameraAccessException.CAMERA_IN_USE) {
                handler.postDelayed({
                    openCameraSafely(handler, context, cameraId, captureSurface)
                }, 500) // Retry after 1 second
            } else {
                throw e
            }
        }
    }

    private fun saveImageData(bitmap: Bitmap, context: Context, imageApplication: String?) {
        // Use the app's private storage directory
        val directory = getImageDirectory(context)

        val file = File(directory, "${imageApplication}_${System.currentTimeMillis()}.jpg")
        try {
            FileOutputStream(file).use { fos ->
                bitmap.compress(Bitmap.CompressFormat.JPEG, 100, fos)
                Log.d("BackgroundRecorderService", "Image saved to ${file.absolutePath}")
            }
        } catch (e: IOException) {
            Log.e("BackgroundRecorderService", "Failed to save image", e)
        }
    }

    private fun checkAndFinalize() {
        // imageReader?.close()
        cameraDevice?.close()
        pendingCaptures--
        if (pendingCaptures == 0) {
            onDestroy()  // Call onDestroy only when all captures are complete
        }
    }

    override fun onDestroy() {
        Log.d("CameraCaptureService", "onDestroy")
        // imageReader?.close()
        cameraDevice?.close()
        stopSelf()
        super.onDestroy()
    }
}

