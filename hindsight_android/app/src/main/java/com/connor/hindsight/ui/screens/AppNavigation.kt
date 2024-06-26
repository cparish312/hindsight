package com.connor.hindsight.ui.screens

import android.os.Build
import androidx.annotation.RequiresApi
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.connor.hindsight.DB
import com.connor.hindsight.models.AnnotationsViewModel
import com.connor.hindsight.models.AnnotationsViewModelFactory

@RequiresApi(Build.VERSION_CODES.O)
@Composable
fun AppNavigation() {
    val navController = rememberNavController()
    val context = LocalContext.current
    NavHost(navController = navController, startDestination = "main") {
        composable("main") {
            MainScreen(onNavigateToScreenRecordingSettings = {
                navController.navigate("screenRecordingSettings")
            }, onNavigateToUploadSettings = {
                    navController.navigate("uploadSettings")
                }, onNavigateToPostQuery = {navController.navigate("postQuery")},
                onNavigateToAnnotations = {navController.navigate("annotationsScreen")})
        }
        composable("screenRecordingSettings") {
            ScreenRecorderSettingsScreen(navController)
        }
        composable("uploadSettings") {
            UploadSettingsScreen(navController)
        }
        composable("postQuery"){
            PostQueryScreen(navController = navController)
        }
        composable("annotationsScreen"){
            val dbHelper = DB(context)
            val viewModel: AnnotationsViewModel = viewModel(
                factory = AnnotationsViewModelFactory(dbHelper)
            )
            AnnotationsScreen(viewModel = viewModel, navController = navController)
        }
    }
}
