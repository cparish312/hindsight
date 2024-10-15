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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.material3.Text
import androidx.compose.ui.platform.LocalContext
import androidx.compose.foundation.Image
import coil.compose.rememberImagePainter
import com.connor.hindsight.DB
import com.connor.hindsight.obj.Content
import com.connor.hindsight.obj.ViewContent
import com.connor.hindsight.utils.openUrl



@Composable
fun FeedScreen(queryViewModel: FeedViewModel = viewModel(), navController: NavController) {
    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background
    ) {
        val context = LocalContext.current
        val dbHelper = DB(context)
        val contentListCursor = dbHelper.getContent(nonViewed = true)
        val contentList = dbHelper.convertCursorToViewContent(contentListCursor).sortedByDescending { it.rankingScore }

        ClickableContainerList(contentList = contentList,
            onContentClick = { contentId: Int, contentUrl: String ->
                val clickedList: List<Int> = listOf(contentId)
                dbHelper.markContentAsClicked(clickedList)
                openUrl(context, contentUrl)
                println("Clicked on: $contentId")
            },
            onContentViewed = { contentId: Int ->
                val viewedList: List<Int> = listOf(contentId)
                dbHelper.markContentAsViewed(viewedList)
                println("Viewed: $contentId")
            },
            onScoreUpdate = { contentId: Int, newScore: Int ->
                dbHelper.updateContentScore(contentId, newScore)
            }
        )
    }
}

@Composable
fun ClickableContainerList(contentList: List<ViewContent>,
                           onContentClick: (Int, String) -> Unit,
                           onContentViewed: (Int) -> Unit,
                           onScoreUpdate: (Int, Int) -> Unit
) {
    val scrollState = rememberLazyListState()
    val viewedItems = remember { mutableStateListOf<Int>() }

    LazyColumn(state = scrollState) {
        itemsIndexed(contentList) { index, content ->
            ClickableContainer(content = content,
                onClick = {onContentClick(content.id, content.url)},
                onScoreUpdate = onScoreUpdate
            )

            LaunchedEffect(key1 = scrollState.firstVisibleItemIndex, key2 = scrollState.firstVisibleItemScrollOffset) {
                if (index == scrollState.firstVisibleItemIndex) {
                    if (!viewedItems.contains(content.id)) {
                        onContentViewed(content.id)
                        viewedItems.add(content.id)
                    }
                }
            }
        }
    }
}

@Composable
fun ClickableContainer(content: ViewContent, onClick: () -> Unit, onScoreUpdate: (Int, Int) -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .background(Color.LightGray, shape = RoundedCornerShape(8.dp))
            .padding(16.dp)
    ) {
        ComposableContainer(
            content = content,
            onScoreUpdate = onScoreUpdate
        )
    }
}


@Composable
fun ComposableContainer(content: ViewContent, onScoreUpdate: (Int, Int) -> Unit) {
    var score by remember { mutableStateOf(content.score) }

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color.White, shape = RoundedCornerShape(8.dp))
            .padding(16.dp)
    ) {
        Column {
            Text(
                text = content.title,
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
                color = Color.DarkGray,
                modifier = Modifier.fillMaxWidth()
            )

            if (!content.thumbnailUrl.isNullOrEmpty()) {
                Image(
                    painter = rememberImagePainter(
                        data = content.thumbnailUrl,
                        builder = {
                            crossfade(true)
                        }
                    ),
                    contentDescription = "Thumbnail",
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(200.dp), // Adjust size as needed
                    contentScale = ContentScale.Crop
                )
                Spacer(modifier = Modifier.height(8.dp))
            }

            content.summary?.let {
                println("Summary: $it")
                Text(
                    text = it,
                    fontSize = 16.sp,
                    color = Color.Gray
                )
                Spacer(modifier = Modifier.height(16.dp))  // Conditionally add space after the summary
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Score Buttons
            Row(
                modifier = Modifier.align(Alignment.End),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Button(
                    onClick = {
                        score = 10
                        content.score = score
                        onScoreUpdate(content.id, score)
                    },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (score == 10) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.secondary
                    )
                ) {
                    Text(text = "↑")
                }
                Button(
                    onClick = {
                        score = -10
                        content.score = score
                        onScoreUpdate(content.id, score)
                    },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (score == -10) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.secondary
                    )
                ) {
                    Text(text = "↓")
                }
                Text(text = "Score: $score", modifier = Modifier.align(Alignment.CenterVertically))
            }
        }
    }
}

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

