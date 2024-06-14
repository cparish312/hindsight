package com.connor.hindsight.ui.screens

import android.os.Build
import androidx.annotation.RequiresApi
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import com.connor.hindsight.utils.Preferences

@RequiresApi(Build.VERSION_CODES.O)
@Composable
fun UploadSettingsScreen(navController: NavController) {
    val screenshotsPerAutoUpload = remember {
        mutableStateOf(
            Preferences.prefs.getInt(Preferences.screenshotsperautoupload, 50).toString()
        )
    }

    Column(
        modifier = Modifier.padding(16.dp)
    ) {
        TextField(
            value = screenshotsPerAutoUpload.value,
            onValueChange = {
                screenshotsPerAutoUpload.value = it
                Preferences.prefs.edit().putInt(
                    Preferences.screenshotsperautoupload,
                    it.toIntOrNull() ?: 50 // Default to 50 if input is not a valid integer
                ).apply()
            },
            label = { Text("Screenshots per Auto Upload") },
            keyboardOptions = KeyboardOptions.Default.copy(keyboardType = KeyboardType.Number)
        )

        Button(
            onClick = {
                navController.navigateUp() // Uses NavController to navigate back
            },
            modifier = Modifier.padding(top = 16.dp)
        ) {
            Text("Back")
        }
    }
}
