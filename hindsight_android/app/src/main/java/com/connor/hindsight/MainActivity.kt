package com.connor.hindsight

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.media.projection.MediaProjectionConfig
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.annotation.RequiresApi
import androidx.compose.runtime.Composable
import androidx.compose.ui.tooling.preview.Preview
import androidx.core.content.ContextCompat
import com.connor.hindsight.models.RecorderModel
import com.connor.hindsight.network.services.ServerUploadService
import com.connor.hindsight.services.RecorderService
import com.connor.hindsight.services.BackgroundRecorderService
import com.connor.hindsight.ui.screens.AppNavigation
import com.connor.hindsight.ui.theme.HindsightTheme
import com.connor.hindsight.utils.Preferences
import com.connor.hindsight.utils.ServerConnectionCallback
import com.connor.hindsight.utils.checkServerConnection

class MainActivity : ComponentActivity() {
    private lateinit var mediaProjectionManager: MediaProjectionManager
    private lateinit var screenCaptureLauncher: ActivityResultLauncher<Intent>
    private val recorderModel: RecorderModel by viewModels()

    @RequiresApi(Build.VERSION_CODES.O)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            HindsightTheme {
                AppNavigation()
            }
        }

        mediaProjectionManager = getSystemService(Context.MEDIA_PROJECTION_SERVICE)
            as MediaProjectionManager
        screenCaptureLauncher = registerForActivityResult(
            ActivityResultContracts.StartActivityForResult()
        ) { result ->
            if (result.resultCode == Activity.RESULT_OK && result.data != null) {
                recorderModel.startVideoRecorder(this, result)
            } else {
                Toast.makeText(this, "Permission Denied", Toast.LENGTH_SHORT).show()
            }
        }

        if (Preferences.prefs.getBoolean(Preferences.screenrecordingenabled, false)) {
            if (!intent.getBooleanExtra(RecorderService.FROM_RECORDER_SERVICE, false)) {
                Log.d("MainActivity", "Starting Recording From MainActivity")
                requestScreenCapturePermission()
            }
        }
    }

    fun requestScreenCapturePermission() {
        if (BackgroundRecorderService.isRunning) {
            Log.d(
                "MainActivity",
                "Ran requestScreenCapturePermission but BackgroundRecorderService is running"
            )
            return
        }
        if (recorderModel.hasScreenRecordingPermissions(this)) {
            Log.d("MainActivity", "hasScreenRecordingPermissions")
            var captureIntent: Intent? = null
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
                // So default val of prompt is entire screen
                val config = MediaProjectionConfig.createConfigForDefaultDisplay()
                captureIntent = mediaProjectionManager.createScreenCaptureIntent(config)
            } else {
                captureIntent = mediaProjectionManager.createScreenCaptureIntent()
            }
            screenCaptureLauncher.launch(captureIntent)
        }
    }

    fun stopScreenRecording() {
        recorderModel.stopRecording(this)
    }

    fun uploadToServer() {
        Log.d("MainActivity", "uploadToServer")
        if (ServerUploadService.isRunning) {
            Log.d(
                "MainActivity",
                "Ran uploadToServer but ServerUploadService is running"
            )
            return
        }
        val primaryUrl: String = Preferences.prefs.getString(
            Preferences.localurl,
            ""
        ).toString()

        checkServerConnection(serverUrl = primaryUrl, object : ServerConnectionCallback {
            override fun onServerStatusChecked(isConnected: Boolean) {
                if (isConnected) {
                    Log.d(
                        "MainActivity",
                        "Connection successful, proceeding with service initialization."
                    )
                    val uploadIntent = Intent(this@MainActivity, ServerUploadService::class.java)
                    ContextCompat.startForegroundService(this@MainActivity, uploadIntent)
                } else {
                    Log.d("MainActivity", "No server connection, aborting upload.")
                }
            }
        })
    }
}

@RequiresApi(Build.VERSION_CODES.O)
@Preview(showBackground = true)
@Composable
fun HindsightPreview() {
    AppNavigation()
}
