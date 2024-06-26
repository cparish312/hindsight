package com.connor.hindsight.models

import android.annotation.SuppressLint
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.connor.hindsight.DB
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

class AnnotationsViewModel(private val dbHelper: DB) : ViewModel() {

    private val _annotations = MutableStateFlow<List<String>>(emptyList())
    val annotations: StateFlow<List<String>> = _annotations

    init {
        loadAnnotations()
    }

    @SuppressLint("Range")
    private fun loadAnnotations() {
        viewModelScope.launch(Dispatchers.IO) {
            val cursor = dbHelper.getAllAnnotations()
            val items = mutableListOf<String>()
            while (cursor.moveToNext()) {
                val text = cursor.getString(cursor.getColumnIndex("text"))
                items.add(text)
            }
            cursor.close()
            _annotations.value = items
        }
    }

    override fun onCleared() {
        dbHelper.close()
        super.onCleared()
    }
}
