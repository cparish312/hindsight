package com.connor.hindsight.obj

data class Content(
    val id: Int,
    val contentGeneratorId: Int,
    val title: String,
    val summary: String?,
    val url: String,
    val topicLabel: String?,
    val thumbnailUrl: String?,
    val publishedDate: Long,
    val rankingScore: Double,
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

data class ViewContent(
    val id: Int,
    val title: String,
    val summary: String?,
    val url: String,
    val topicLabel: String?,
    val thumbnailUrl: String?,
    var score: Int,
    var rankingScore: Double
)

data class ContentRanking(
    val id: Int,
    var rankingScore: Double
)