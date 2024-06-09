package com.connor.hindsight.ui.screens

import android.os.Build
import androidx.annotation.RequiresApi
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import com.connor.hindsight.ui.components.SettingsToggleButton
import com.connor.hindsight.utils.Preferences

@RequiresApi(Build.VERSION_CODES.O)
@Composable
fun ScreenRecorderSettingsScreen(navController: NavController) {
    val recordWhenActive = remember {
        mutableStateOf(
            Preferences.prefs.getBoolean(Preferences.recordwhenactive, false)
        )
    }

    Column(
        modifier = Modifier.padding(16.dp)
    ) {
        SettingsToggleButton(
            checked = recordWhenActive.value,
            text = "Only Take Screenshot when User is Active (requires Accessibility API)",
            onToggleOn = {
                Preferences.prefs.edit().putBoolean(Preferences.recordwhenactive, true).apply()
                recordWhenActive.value = true
            },
            onToggleOff = {
                Preferences.prefs.edit().putBoolean(Preferences.recordwhenactive, false).apply()
                recordWhenActive.value = false
            }
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
