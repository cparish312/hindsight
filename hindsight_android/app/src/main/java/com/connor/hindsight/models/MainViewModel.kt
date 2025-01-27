package com.connor.hindsight.models

import android.app.Application
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import android.util.Log
import androidx.annotation.RequiresApi
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.connor.hindsight.network.services.ServerUploadService
import com.connor.hindsight.services.BackgroundRecorderService
import com.connor.hindsight.utils.Preferences
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.launch

@RequiresApi(Build.VERSION_CODES.O)
class MainViewModel(application: Application) : AndroidViewModel(application) {

    private val _screenRecordingEnabled = MutableStateFlow(
        Preferences.prefs.getBoolean(Preferences.screenrecordingenabled, false)
    )
    val screenRecordingEnabled = _screenRecordingEnabled.asStateFlow()

    private val _locationTrackingEnabled = MutableStateFlow(
        Preferences.prefs.getBoolean(Preferences.locationtrackingenabled, false)
    )
    val locationTrackingEnabled = _locationTrackingEnabled.asStateFlow()

    private val _cameraCaptureEnabled = MutableStateFlow(
        Preferences.prefs.getBoolean(Preferences.cameracaptureenabled, false)
    )
    val cameraCaptureEnabled = _cameraCaptureEnabled.asStateFlow()

    private val _isUploading = MutableStateFlow(false)
    val isUploading = _isUploading.asStateFlow()

    private val _keyloggingEnabled = MutableStateFlow(false)
    val keyloggingEnabled = _keyloggingEnabled.asStateFlow()

    private val _eventChannel = Channel<UIEvent>()
    val events = _eventChannel.receiveAsFlow()

    private val broadcastReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            when (intent?.action) {
                ServerUploadService.UPLOADER_FINISHED -> {
                    Log.d("MainViewModel", "UPLOADER_FINISHED")
                    _isUploading.value = false
                }
                ServerUploadService.UPLOADER_STARTED -> {
                    Log.d("MainViewModel", "UPLOADER_STARTED")
                    _isUploading.value = true
                }
                BackgroundRecorderService.SCREEN_RECORDER_STOPPED -> {
                    Log.d("MainViewModel", "SCREEN_RECORDER_STOPPED")
                    _screenRecordingEnabled.value = false
                    Preferences.prefs.edit().putBoolean(
                        Preferences.screenrecordingenabled,
                        _screenRecordingEnabled.value
                    ).apply()
                }
                RecorderModel.SCREEN_RECORDER_PERMISSION_DENIED -> {
                    Log.d("MainViewModel", RecorderModel.SCREEN_RECORDER_PERMISSION_DENIED)
                    _screenRecordingEnabled.value = false
                    Preferences.prefs.edit().putBoolean(
                        Preferences.screenrecordingenabled,
                        _screenRecordingEnabled.value
                    ).apply()
                }
            }
        }
    }

    init {
        val intentFilter = IntentFilter().apply {
            addAction(ServerUploadService.UPLOADER_FINISHED)
            addAction(ServerUploadService.UPLOADER_STARTED)
            addAction(BackgroundRecorderService.SCREEN_RECORDER_STOPPED)
            addAction(RecorderModel.SCREEN_RECORDER_PERMISSION_DENIED)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            getApplication<Application>().registerReceiver(
                broadcastReceiver,
                intentFilter,
                Context.RECEIVER_EXPORTED
            )
        } else {
            getApplication<Application>().registerReceiver(broadcastReceiver, intentFilter,
                Context.RECEIVER_NOT_EXPORTED)
        }
    }

    fun toggleScreenRecording() {
        _screenRecordingEnabled.value = !_screenRecordingEnabled.value
        Preferences.prefs.edit().putBoolean(Preferences.screenrecordingenabled, _screenRecordingEnabled.value)
            .apply()

        viewModelScope.launch {
            if (_screenRecordingEnabled.value) {
                _eventChannel.send(UIEvent.RequestScreenCapturePermission)
            } else {
                _eventChannel.send(UIEvent.StopScreenRecording)
            }
        }
    }

    fun toggleLocationTracking() {
        _locationTrackingEnabled.value = !_locationTrackingEnabled.value
        Preferences.prefs.edit().putBoolean(Preferences.locationtrackingenabled, _locationTrackingEnabled.value)
            .apply()
    }

    fun toggleCameraCapture() {
        _cameraCaptureEnabled.value = !_cameraCaptureEnabled.value
        Preferences.prefs.edit().putBoolean(Preferences.cameracaptureenabled, _cameraCaptureEnabled.value)
            .apply()
    }

    fun toggleKeylogging() {
        _keyloggingEnabled.value = !_keyloggingEnabled.value
    }

    override fun onCleared() {
        super.onCleared()
        getApplication<Application>().unregisterReceiver(broadcastReceiver)
    }

    sealed class UIEvent {
        object RequestScreenCapturePermission : UIEvent()
        object StopScreenRecording : UIEvent()
    }
}
