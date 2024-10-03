package com.connor.hindsight.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*  // Required for Column and other layouts
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.background
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.foundation.rememberScrollState

import androidx.activity.compose.setContent
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.connor.hindsight.R  // Import your own drawable resources
import com.connor.hindsight.models.FeedViewModel
import com.connor.hindsight.models.QueryViewModel

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.material3.Text



@Composable
fun FeedScreen(queryViewModel: FeedViewModel = viewModel(), navController: NavController) {
    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background
    ) {
        ClickableContainerList(items = List(20) { "Item #$it" }) { clickedItem ->
            // Handle the click event for the clicked item
            println("Clicked on: $clickedItem")
        }
    }
}

@Composable
fun ClickableContainerList(items: List<String>, onItemClick: (String) -> Unit) {
    val scrollState = rememberScrollState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(scrollState)
            .padding(16.dp)
    ) {
        HorizontalScrollablePills(
            pills = listOf(
                PillData("Kotlin", Color.Red),
                PillData("Compose", Color.Blue),
                PillData("Jetpack", Color.Green),
                PillData("Android", Color.Magenta),
                PillData("Coroutines", Color.Cyan),
                PillData("State", Color.Yellow),
                PillData("UI", Color.Gray),
                PillData("Architecture", Color.Black)
            )
        )
        items.forEach { item ->
            ClickableContainer(item = item, onClick = { onItemClick(item) })
            Spacer(modifier = Modifier.height(8.dp)) // Spacing between containers
        }
    }
}

@Composable
fun ClickableContainer(item: String, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .background(Color.LightGray, shape = RoundedCornerShape(8.dp))
            .padding(16.dp)
    ) {
//        Text(
//            text = item,
//            fontSize = 18.sp,
//            fontWeight = FontWeight.Bold,
//            color = Color.Black
//        )
        ComposableContainer(
            R.drawable.ic_notification,
            "Title",
            "Body text."
        )
    }
}


@Composable
fun ComposableContainer(iconRes: Int, headline: String, bodyText: String) {
    var score by remember { mutableStateOf(0) }

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color.White, shape = RoundedCornerShape(8.dp))
            .padding(16.dp)
    ) {
        Column {
            Row(verticalAlignment = Alignment.CenterVertically) {
                // Image Icon
                Image(
                    painter = painterResource(id = iconRes),
                    contentDescription = "Icon",
                    modifier = Modifier
                        .size(64.dp)
                        .padding(end = 16.dp),
                    contentScale = ContentScale.Crop
                )
                // Headline
                Text(
                    text = headline,
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.fillMaxWidth()
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Text Body
            Text(
                text = bodyText,
                fontSize = 16.sp,
                color = Color.Gray
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Score Button
            Button(
                onClick = { score++ },
                modifier = Modifier.align(Alignment.End)
            ) {
                Text(text = "Score: $score")
            }
        }
    }
}

//------------- scrollable pill stuff---------------------//
data class PillData(val text: String, val color: Color)

@Composable
fun HorizontalScrollablePills(pills: List<PillData>) {
    Row(
        modifier = Modifier
            .horizontalScroll(rememberScrollState())  // Enables horizontal scrolling
            .padding(8.dp)
            .background(Color.Magenta)
    ) {
        pills.forEach { pill ->
            Pill(text = pill.text, color = pill.color)
            Spacer(modifier = Modifier.width(8.dp)) // Space between pills
        }
    }
}

@Composable
fun Pill(text: String, color: Color) {
    Box(
        modifier = Modifier
            .background(color = color, shape = RoundedCornerShape(16.dp))
            .padding(horizontal = 16.dp, vertical = 8.dp) // Padding inside the pill
            .border(BorderStroke(1.dp, Color.Yellow))
    ) {
        Text(
            text = text,
            color = Color.Black,
            fontSize = 16.sp,
            fontWeight = FontWeight.Bold
        )
    }
}

