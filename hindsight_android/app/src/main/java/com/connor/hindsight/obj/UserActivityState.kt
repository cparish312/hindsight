package com.connor.hindsight.obj

object UserActivityState {
    @Volatile var userActive: Boolean = false
    @Volatile var currentApplication: String? = "screenshot"
}
