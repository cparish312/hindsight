package com.connor.hindsight

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import androidx.activity.ComponentActivity
import android.content.Context
import android.content.Intent
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.activity.compose.setContent
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.runtime.Composable
import androidx.compose.ui.tooling.preview.Preview
import androidx.core.content.ContextCompat
import com.connor.hindsight.services.ScreenRecordingService_o
import com.connor.hindsight.ui.screens.MainScreen
import com.connor.hindsight.utils.Constants
import com.connor.hindsight.utils.PermissionHelper
import com.connor.hindsight.ui.models.RecorderModel

class MainActivity : ComponentActivity() {
    companion object {
        private const val WRITE_REQUEST_CODE = 1  // Arbitrary integer, but should be unique within your Activity.
    }

    private lateinit var mediaProjectionManager: MediaProjectionManager
    private lateinit var screenCaptureLauncher: ActivityResultLauncher<Intent>
    private lateinit var writePermissionRequest: ActivityResultLauncher<Intent>
    private val recorderModel: RecorderModel by viewModels()


    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MainScreen()
        }

//        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
//            try {
//                Log.d("MainActivity", "Attempting Request Permission")
//                val pendingIntent = MediaStore.createWriteRequest(
//                    contentResolver,
//                    listOf(MediaStore.Images.Media.EXTERNAL_CONTENT_URI)
//                )
//                val intent = IntentSenderRequest.Builder(pendingIntent.intentSender).build()
//                writeRequestLauncher.launch(intent)
//            } catch (e: SecurityException) {
//                Toast.makeText(this, "Failed to request permission: ${e.message}", Toast.LENGTH_SHORT).show();
//            }
//        }

        mediaProjectionManager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        screenCaptureLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            if (result.resultCode == Activity.RESULT_OK && result.data != null) {
                recorderModel.startVideoRecorder(this, result)
            } else {
                Toast.makeText(this, "Permission Denied", Toast.LENGTH_SHORT).show()
            }
        }
//        screenCaptureLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
//            if (result.resultCode == Activity.RESULT_OK && result.data != null) {
//                val intent = Intent(this, ScreenRecordingService_o::class.java).apply {
//                    action = Constants.ACTION_START_SCREEN_CAPTURE
//                    putExtra("resultCode", result.resultCode)
//                    putExtra("dataIntent", result.data)
//                }
//                ContextCompat.startForegroundService(this, intent)
//            } else {
//                Toast.makeText(this, "Permission Denied", Toast.LENGTH_SHORT).show()
//            }
//        }
    }

    fun requestScreenCapturePermission() {
        if (recorderModel.hasScreenRecordingPermissions(this)) {
            Log.d("MainActivity", "hasScreenRecordingPermissions")
            val captureIntent = mediaProjectionManager.createScreenCaptureIntent()
            screenCaptureLauncher.launch(captureIntent)
        }
    }

    fun stopScreenRecording() {
        recorderModel.stopRecording()
//        val intent = Intent(this, ScreenRecordingService_o::class.java).apply {
//            action = Constants.ACTION_STOP_SCREEN_CAPTURE
//        }
//        startService(intent)
    }

    private val writeRequestLauncher = registerForActivityResult(ActivityResultContracts.StartIntentSenderForResult()) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            // The user granted write permissions
            Toast.makeText(this, "Permission granted", Toast.LENGTH_SHORT).show()
        } else {
            // The user didn't grant permissions
            Toast.makeText(this, "Permission denied", Toast.LENGTH_SHORT).show()
        }
    }

}



@Preview(showBackground = true)
@Composable
fun HindsightPreview() {
    MainScreen()
}