package com.connor.hindsight.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.connor.hindsight.MainActivity
import com.connor.hindsight.models.PostQueryViewModel
import com.connor.hindsight.ui.components.showDatePicker
import java.util.Date

@Composable
fun PostQueryScreen(postQueryViewModel: PostQueryViewModel = viewModel(), navController: NavController) {
    var query by remember { mutableStateOf("") }
    var startTimeMillis by remember { mutableStateOf<Long?>(null) }
    var endTimeMillis by remember { mutableStateOf<Long?>(null) }
    val context = LocalContext.current

    Column(modifier = Modifier.padding(16.dp)) {
        OutlinedTextField(
            value = query,
            onValueChange = { query = it },
            label = { Text("Query") },
            keyboardOptions = KeyboardOptions.Default.copy(imeAction = ImeAction.Next)
        )

        Button(onClick = {
            showDatePicker(context) { millis ->
                startTimeMillis = millis // Set the time in milliseconds
            }
        }) {
            Text(if (startTimeMillis != null) "Start Date: ${Date(startTimeMillis!!).toString()}" else "Pick Start Date")
        }

        Button(onClick = {
            showDatePicker(context) { millis ->
                endTimeMillis = millis // Set the time in milliseconds
            }
        }) {
            Text(if (endTimeMillis != null) "End Date: ${Date(endTimeMillis!!).toString()}" else "Pick End Date")
        }

        Button(
            onClick = { if (context is MainActivity) {
                postQueryViewModel.postQuery(query, startTimeMillis, endTimeMillis, context)
            }},
            modifier = Modifier.padding(top = 16.dp)
        ) {
            Text("Submit")
        }
        Button(
            onClick = {
                navController.navigateUp()
            },
            modifier = Modifier.padding(top = 16.dp)
        ) {
            Text("Back")
        }
    }
}
