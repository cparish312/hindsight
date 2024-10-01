package com.connor.hindsight.obj

data class Content(
    val id: Int,
    val contentGeneratorId: Int,
    val title: String,
    val url: String,
    val thumbnailUrl: String?,
    val publishedDate: Long,
    val rankingScore: Float,
    val score: Int?,
    val clicked: Boolean,
    val viewed: Boolean,
    val urlIsLocal: Boolean,
    val contentGeneratorSpecificData: String?,
    val lastModifiedTimestamp: Long
)

// SyncContent to minimize data transfer to only what can be modified by the app
data class SyncContent(
    val id: Int,
    val lastModifiedTimestamp: Long,
    val viewed: Boolean,
    val score: Int,
    val clicked: Boolean
)