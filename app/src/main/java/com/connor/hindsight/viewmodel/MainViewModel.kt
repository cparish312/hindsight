package com.connor.hindsight.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.receiveAsFlow


class MainViewModel : ViewModel() {
    private val _screenRecordingEnabled = MutableStateFlow(false)
    val screenRecordingEnabled = _screenRecordingEnabled.asStateFlow()

    private val _locationTrackingEnabled = MutableStateFlow(false)
    val locationTrackingEnabled = _locationTrackingEnabled.asStateFlow()

    private val _keyloggingEnabled = MutableStateFlow(false)
    val keyloggingEnabled = _keyloggingEnabled.asStateFlow()

    private val _eventChannel = Channel<UIEvent>()
    val events = _eventChannel.receiveAsFlow()

    fun toggleScreenRecording() {
        _screenRecordingEnabled.value = !_screenRecordingEnabled.value

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

    sealed class UIEvent {
        object RequestScreenCapturePermission : UIEvent()
        object StopScreenRecording : UIEvent()
    }

}