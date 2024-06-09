package com.connor.hindsight.utils

import android.content.Context
import java.io.File

fun getImageFiles(directory: File): List<File> {
    return directory.listFiles { _, name -> name.endsWith(".jpg") }?.toList() ?: emptyList()
}

fun getImageDirectory(context: Context): File {
    val directory = File(context.filesDir, "screenshot_images")
    if (!directory.exists()) directory.mkdirs() // Ensure the directory exists
    return directory
}

fun getSyncedImageDirectory(context: Context): File {
    val directory = File(context.filesDir, "synced_screenshot_images")
    if (!directory.exists()) directory.mkdirs() // Ensure the directory exists
    return directory
}
