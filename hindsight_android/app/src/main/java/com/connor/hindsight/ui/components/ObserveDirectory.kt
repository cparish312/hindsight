package com.connor.hindsight.ui.components

import java.io.File
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow

fun observeDirectory(directory: File): Flow<Int> = flow {
    while (true) {
        val files = directory.listFiles()
        val count = files?.size ?: 0
        emit(count)
        delay(2000) // Check every 5 seconds
    }
}
