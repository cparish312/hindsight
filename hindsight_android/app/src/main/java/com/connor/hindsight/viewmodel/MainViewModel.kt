package com.connor.hindsight.viewmodel

import android.app.Application
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.SharedPreferences
import android.os.AsyncTask
import android.os.Build
import android.util.Log
import androidx.annotation.RequiresApi
import androidx.core.content.ContextCompat
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.receiveAsFlow
import java.net.HttpURLConnection
import java.net.URL
import com.connor.hindsight.network.services.PostService
import com.connor.hindsight.services.RecorderService
import com.connor.hindsight.services.ScreenRecorderService

@RequiresApi(Build.VERSION_CODES.O)
class MainViewModel(application: Application) : AndroidViewModel(application) {
    private val prefs: SharedPreferences = application.getSharedPreferences("AppPrefs", Context.MODE_PRIVATE)

    private val _screenRecordingEnabled = MutableStateFlow(prefs.getBoolean("ScreenRecordingEnabled", false))
    val screenRecordingEnabled = _screenRecordingEnabled.asStateFlow()

    private val _isUploading = MutableStateFlow(false)
    val isUploading = _isUploading.asStateFlow()

    private val _locationTrackingEnabled = MutableStateFlow(false)
    val locationTrackingEnabled = _locationTrackingEnabled.asStateFlow()

    private val _keyloggingEnabled = MutableStateFlow(false)
    val keyloggingEnabled = _keyloggingEnabled.asStateFlow()

    private val _eventChannel = Channel<UIEvent>()
    val events = _eventChannel.receiveAsFlow()

    private val broadcastReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            when (intent?.action) {
                PostService.UPLOADER_FINISHED -> {
                    Log.d("MainViewModel", "UPLOADER_FINISHED")
                    _isUploading.value = false
                }
                ScreenRecorderService.SCREEN_RECORDER_STOPPED -> {
                    Log.d("MainViewModel", "SCREEN_RECORDER_STOPPED")
                    _screenRecordingEnabled.value = false
                    prefs.edit().putBoolean("ScreenRecordingEnabled", _screenRecordingEnabled.value).apply()
                }
            }
        }
    }

    init {
        val intentFilter = IntentFilter().apply {
            addAction(PostService.UPLOADER_FINISHED)
            addAction(ScreenRecorderService.SCREEN_RECORDER_STOPPED)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            getApplication<Application>().registerReceiver(broadcastReceiver, intentFilter, Context.RECEIVER_EXPORTED)
        } else {
            getApplication<Application>().registerReceiver(broadcastReceiver, intentFilter)
        }
    }

    fun toggleScreenRecording() {
        _screenRecordingEnabled.value = !_screenRecordingEnabled.value
        prefs.edit().putBoolean("ScreenRecordingEnabled", _screenRecordingEnabled.value).apply()

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
    }

    fun toggleKeylogging() {
        _keyloggingEnabled.value = !_keyloggingEnabled.value
    }

    fun serverUploadPresssed() {
        _isUploading.value = true
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