package com.connor.hindsight.ui.screens
import android.os.Build
import android.util.Log
import androidx.annotation.RequiresApi
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.connor.hindsight.MainActivity
import com.connor.hindsight.models.MainViewModel
import com.connor.hindsight.ui.components.ToggleButton
import com.connor.hindsight.ui.components.observeDirectory
import com.connor.hindsight.utils.getImageDirectory
import kotlinx.coroutines.ExperimentalCoroutinesApi

@RequiresApi(Build.VERSION_CODES.O)
@Composable
fun MainScreen(
    mainViewModel: MainViewModel = viewModel(),
    onNavigateToScreenRecordingSettings: () -> Unit,
    onNavigateToUploadSettings: () -> Unit,
    onNavigateToPostQuery: () -> Unit,
) {
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

        val imageDir = getImageDirectory(context)
        val fileCountFlow = remember { observeDirectory(imageDir) }

        @OptIn(ExperimentalCoroutinesApi::class)
        val fileCount = fileCountFlow.collectAsState(initial = 0).value

        ToggleButton(
            checked = screenRecordingEnabled.value,
            text = "Screen Recording",
            onToggleOn = mainViewModel::toggleScreenRecording,
            onToggleOff = mainViewModel::toggleScreenRecording,
            onClickSettings = onNavigateToScreenRecordingSettings
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

        Row(
            modifier = Modifier.padding(top = 16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Button(
                onClick = {
                    if (context is MainActivity) {
                        if (!isUploading.value) {
                            context.uploadToServer()
                        }
                    }
                },
                modifier = Modifier.align(Alignment.CenterVertically).padding(top = 16.dp).padding(
                    16.dp
                )
            ) {
                Text("Server Upload")
            }
            if (isUploading.value) {
                CircularProgressIndicator(
                    modifier = Modifier.align(Alignment.CenterVertically).padding(top = 16.dp)
                )
            }
            IconButton(onClick = onNavigateToUploadSettings) {
                Icon(
                    imageVector = Icons.Filled.Settings,
                    contentDescription = "Settings",
                    modifier = Modifier.align(Alignment.CenterVertically).padding(top = 16.dp)
                )
            }
        }

        Text(
            "Unsynced Screenshots: $fileCount",
            modifier = Modifier.padding(16.dp)
        )

        Button(
            onClick = onNavigateToPostQuery,
            modifier = Modifier.padding(16.dp)
        ) {
            Text("Query")
        }
    }
}
