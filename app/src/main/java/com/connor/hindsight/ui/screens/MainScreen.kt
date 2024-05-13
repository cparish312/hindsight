package com.connor.hindsight.ui.screens
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Settings
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.lifecycle.viewmodel.compose.viewModel
import com.connor.hindsight.MainActivity
import com.connor.hindsight.viewmodel.MainViewModel

@Composable
fun MainScreen(mainViewModel: MainViewModel = viewModel()) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current

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
    }
}

@Composable
fun ToggleButton(
    checked: Boolean,
    text: String,
    onToggleOn: () -> Unit,
    onToggleOff: () -> Unit,
    onClickSettings: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(text = text)
        Switch(
            checked = checked,
            onCheckedChange = { isChecked ->
                if (isChecked) {
                    onToggleOn()
                } else {
                    onToggleOff()
                }
            }
        )
        IconButton(onClick = onClickSettings) {
            Icon(
                imageVector = Icons.Filled.Settings,
                contentDescription = "Settings"
            )
        }
    }
}