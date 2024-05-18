package com.connor.hindsight.services

import android.accessibilityservice.AccessibilityService
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import com.connor.hindsight.obj.UserActivityState

class KeyTrackingService : AccessibilityService() {
    override fun onAccessibilityEvent(event: AccessibilityEvent) {
        UserActivityState.userActive = true
    }

    override fun onCreate() {
        Log.d("KeyTrackingService", "onCreate")
        super.onCreate()
    }
    override fun onInterrupt() {
    }
}