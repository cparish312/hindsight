package com.connor.hindsight.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import com.connor.hindsight.models.AnnotationsViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AnnotationsScreen(viewModel: AnnotationsViewModel, navController: NavController) {
    val annotations = viewModel.annotations.collectAsState().value

    Scaffold(
        topBar = {
            TopAppBar(title = { Text("Annotations") })
        },
        content = { padding ->
            Column(modifier = Modifier.padding(padding)) {
                LazyColumn {
                    items(annotations) { annotation ->
                        AnnotationItem(annotation)
                    }
                }
                Button(
                    onClick = { navController.navigateUp() },
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp)
                ) {
                    Text("Back")
                }
            }
        }
    )
}

@Composable
fun AnnotationItem(annotation: String) {
    Card(
        modifier = Modifier
            .padding(all = 8.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(text = annotation, style = MaterialTheme.typography.bodyLarge)
        }
    }
}