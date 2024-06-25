package com.connor.hindsight.services

import android.accessibilityservice.AccessibilityService
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import com.connor.hindsight.obj.UserActivityState

class KeyTrackingService : AccessibilityService() {
    override fun onAccessibilityEvent(event: AccessibilityEvent) {
        UserActivityState.userActive = true
        if (event.eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED ||
            event.eventType == AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED) {
            try {
                event.packageName?.let {
                    val packageName = event.packageName.toString().replace(".", "-")
                    UserActivityState.currentApplication = packageName
                    Log.d("KeyTrackingService", "onAccessibilityEvent: $packageName")
                }
            } catch(e: Error){
                Log.d("KeyTrackingService", "Error getting packageName", e)
            }
        }
    }

    override fun onCreate() {
        Log.d("KeyTrackingService", "onCreate")
        super.onCreate()
    }
    override fun onInterrupt() {
    }
}
