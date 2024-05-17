package com.connor.hindsight.ui.screens
import android.os.Build
import android.util.Log
import androidx.annotation.RequiresApi
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.viewmodel.compose.viewModel
import com.connor.hindsight.MainActivity
import com.connor.hindsight.viewmodel.MainViewModel
import com.connor.hindsight.ui.components.ToggleButton

@RequiresApi(Build.VERSION_CODES.O)
@Composable
fun MainScreen(mainViewModel: MainViewModel = viewModel()) {
    val context = LocalContext.current

    LaunchedEffect(key1 = mainViewModel) {
        mainViewModel.events.collect { event ->
            when (event) {
                MainViewModel.UIEvent.RequestScreenCapturePermission -> {
                    if (context is MainActivity) {
                        context.requestScreenCapturePermission()
                    }
                }
                MainViewModel.UIEvent.StopScreenRecording -> {
                    if (context is MainActivity) {
                        Log.d("MainScreen", "Stopping screen recording")
                        context.stopScreenRecording()
                    }
                }
            }
        }
    }

    Column(
        modifier = Modifier.padding(16.dp)
    ) {
        val screenRecordingEnabled = mainViewModel.screenRecordingEnabled.collectAsState()
        val isUploading = mainViewModel.isUploading.collectAsState()
        val locationTrackingEnabled = mainViewModel.locationTrackingEnabled.collectAsState()
        val keyloggingEnabled = mainViewModel.keyloggingEnabled.collectAsState()

        ToggleButton(
            checked = screenRecordingEnabled.value,
            text = "Screen Recording",
            onToggleOn = mainViewModel::toggleScreenRecording,
            onToggleOff = mainViewModel::toggleScreenRecording,
            onClickSettings = { /* Open settings for screen recording */ }
        )

        ToggleButton(
            checked = locationTrackingEnabled.value,
            text = "Location Tracking",
            onToggleOn = mainViewModel::toggleLocationTracking,
            onToggleOff = mainViewModel::toggleLocationTracking,
            onClickSettings = { /* Open settings for location tracking */ }
        )

        ToggleButton(
            checked = keyloggingEnabled.value,
            text = "Keystroke Tracking",
            onToggleOn = mainViewModel::toggleKeylogging,
            onToggleOff = mainViewModel::toggleKeylogging,
            onClickSettings = { /* Open settings for keystroke tracking */ }
        )

        Row(modifier = Modifier.padding(top = 16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically){
            Button(onClick = { if (context is MainActivity) {
                if (!isUploading.value){
                    context.uploadToServer()
                }
                mainViewModel.serverUploadPresssed()} },
                modifier = Modifier.align(Alignment.CenterVertically).padding(top = 16.dp).padding(16.dp)) {
                Text("Server Upload")
            }
            if (isUploading.value) {
                CircularProgressIndicator(modifier = Modifier.align(Alignment.CenterVertically).padding(top = 16.dp))
            }
        }
    }
}