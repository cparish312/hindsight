package com.connor.hindsightmobile.ui.elements

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun ToggleButton(
    checked: Boolean,
    text: String,
    onToggleOn: () -> Unit,
    onToggleOff: () -> Unit,
    onClickSettings: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(text = text)
        Switch(
            checked = checked,
            onCheckedChange = { isChecked ->
                if (isChecked) {
                    onToggleOn()
                } else {
                    onToggleOff()
                }
            }
        )
        IconButton(onClick = onClickSettings) {
            Icon(
                imageVector = Icons.Filled.Settings,
                contentDescription = "Settings"
            )
        }
    }
}
