package com.connor.hindsight.ui.screens

import android.os.Build
import androidx.annotation.RequiresApi
import androidx.compose.runtime.Composable
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController

@RequiresApi(Build.VERSION_CODES.O)
@Composable
fun AppNavigation() {
    val navController = rememberNavController()
    NavHost(navController = navController, startDestination = "main") {
        composable("main") {
            MainScreen(onNavigateToScreenRecordingSettings = {
                navController.navigate("screenRecordingSettings")
            }, onNavigateToUploadSettings = {
                navController.navigate("uploadSettings")
            })
        }
        composable("screenRecordingSettings") {
            ScreenRecorderSettingsScreen(navController)
        }
        composable("uploadSettings") {
            UploadSettingsScreen(navController)
        }
    }
}
