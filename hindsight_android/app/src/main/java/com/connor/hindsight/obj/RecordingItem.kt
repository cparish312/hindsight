package com.connor.hindsight.obj

import android.graphics.Bitmap
import androidx.documentfile.provider.DocumentFile
import com.connor.hindsight.enums.RecorderType

data class RecordingItemData(
    val recordingFile: DocumentFile,
    val recorderType: RecorderType,
    val thumbnail: Bitmap? = null
) {
    val isVideo get() = recorderType == RecorderType.VIDEO
}
