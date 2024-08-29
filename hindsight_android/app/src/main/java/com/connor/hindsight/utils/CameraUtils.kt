package com.connor.hindsight.utils

import android.content.Context
import android.content.pm.PackageManager
import android.hardware.camera2.CameraAccessException
import android.hardware.camera2.CameraCaptureSession
import android.hardware.camera2.CameraDevice
import android.hardware.camera2.CameraManager
import android.hardware.camera2.CameraMetadata
import android.hardware.camera2.CaptureRequest
import android.view.Surface
import androidx.core.app.ActivityCompat
import android.Manifest
import android.os.Handler
import android.util.Log


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
            override fun onOpened(cameraDevice: CameraDevice) {
                Log.d("CameraAccess", "Camera opened successfully")
                try {
                    createCameraCaptureSession(cameraDevice, captureSurface)
                } catch (e: Exception) {
                    Log.e("CameraAccess", "Failed to handle camera properly", e)
                }
            }

            override fun onDisconnected(cameraDevice: CameraDevice) {
                cameraDevice.close()
            }

            override fun onError(cameraDevice: CameraDevice, error: Int) {
                cameraDevice.close()
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
            }, 1000) // Retry after 1 second
        } else {
            throw e
        }
    }
}

