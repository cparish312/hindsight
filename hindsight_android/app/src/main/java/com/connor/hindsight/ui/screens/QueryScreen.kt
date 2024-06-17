package com.connor.hindsight.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.Divider
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.runtime.livedata.observeAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.connor.hindsight.MainActivity
import com.connor.hindsight.models.QueryViewModel
import com.connor.hindsight.ui.components.showDatePicker
import java.util.Date

@Composable
fun PostQueryScreen(queryViewModel: QueryViewModel = viewModel(), navController: NavController) {
    var query by remember { mutableStateOf("") }
    var startTimeMillis by remember { mutableStateOf<Long?>(null) }
    var endTimeMillis by remember { mutableStateOf<Long?>(null) }
    val context = LocalContext.current

    val queries = queryViewModel.queries.observeAsState(initial = listOf()).value

    LaunchedEffect(key1 = true) {
        queryViewModel.fetchQueries()
    }

    Column(modifier = Modifier.padding(16.dp)) {
        OutlinedTextField(
            value = query,
            onValueChange = { query = it },
            label = { Text("Query") },
            keyboardOptions = KeyboardOptions.Default.copy(imeAction = ImeAction.Next),
            textStyle = TextStyle(color = Color.Black, fontSize = 16.sp)
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
                queryViewModel.postQuery(query, startTimeMillis, endTimeMillis, context)
                query = ""
                startTimeMillis = null
                endTimeMillis = null
            }},
            modifier = Modifier.padding(top = 16.dp)
        ) {
            Text("Submit")
        }

        Row(
            modifier = Modifier.padding(top = 16.dp).fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Button(
                onClick = {
                    navController.navigateUp()
                },
                modifier = Modifier.padding(top = 16.dp)
            ) {
                Text("Back")
            }

            Spacer(Modifier.width(8.dp))

            Button(
                onClick = {
                    queryViewModel.fetchQueries()
                },
                modifier = Modifier.padding(top = 16.dp)
            ) {
                Text("Fetch Queries")
            }
        }

        LazyColumn(modifier = Modifier.padding(top = 8.dp)) {
            itemsIndexed(queries) { index, query ->
                if (index > 0) {
                    Divider(modifier = Modifier.padding(vertical = 4.dp), thickness = 1.dp)
                }
                Text(text = query, modifier = Modifier.padding(8.dp))
            }
        }
    }
}
