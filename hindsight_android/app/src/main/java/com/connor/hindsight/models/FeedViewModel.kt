package com.connor.hindsight.models

import androidx.lifecycle.ViewModel
import com.connor.hindsight.DB
import com.connor.hindsight.obj.Content
import kotlinx.coroutines.*
import kotlin.random.Random

class FeedViewModel : ViewModel() {
    // List to store topics
    private var topics: MutableList<String> = mutableListOf()

    // Scope for managing coroutines (could also use ViewModelScope if in Android ViewModel)
    private val scope = CoroutineScope(Dispatchers.Default)

    // Function to get the current list of topics
    fun getTopics(): List<String> {
        return topics.toList()  // Return an immutable copy
    }

    // Function to update topics periodically
    fun startUpdatingTopics() {
        scope.launch {
            while (isActive) { // Keep updating until cancelled
                delay(5000) // Delay for 5 seconds before updating
                updateTopics()
            }
        }
    }

    // Function to manually update topics (for testing or other uses)
    fun updateTopics() {
        val newTopics = generateRandomTopics()
        topics.clear()
        topics.addAll(newTopics)
        onTopicsUpdated(newTopics)
    }

    // Function to stop updating topics
    fun stopUpdatingTopics() {
        scope.cancel()  // Cancel the coroutine scope to stop updates
    }

    // Generate some random topics (this simulates fetching or creating new topics)
    private fun generateRandomTopics(): List<String> {
        val randomTopics = listOf(
            "Kotlin Programming", "Jetpack Compose", "Android Development",
            "Coroutines", "State Management", "UI Design", "Architecture Components",
            "Networking", "Testing", "Performance Optimization"
        )
        return randomTopics.shuffled().take(Random.nextInt(3, 6))  // Randomly pick 3-5 topics
    }

    // Callback function when topics are updated (you can change this to notify UI)
    private fun onTopicsUpdated(newTopics: List<String>) {
        println("Topics updated: $newTopics")
    }

}