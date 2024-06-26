package com.connor.hindsight.models

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import com.connor.hindsight.DB

class AnnotationsViewModelFactory(private val dbHelper: DB) : ViewModelProvider.Factory {
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(AnnotationsViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST")
            return AnnotationsViewModel(dbHelper) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class")
    }
}
