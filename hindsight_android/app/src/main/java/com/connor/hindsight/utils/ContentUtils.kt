package com.connor.hindsight.utils

import com.connor.hindsight.obj.Content
import com.connor.hindsight.obj.ContentRanking
import org.json.JSONArray
import org.json.JSONObject

data class ParsedContentResponse(
    val contentList: List<Content>,
    val newlyViewedContentIds: List<Int>,
    val contentRankingScoresList: List<ContentRanking>
)

fun parseJsonToContentResponse(json: String): ParsedContentResponse {
    val jsonObject = JSONObject(json)

    // Parse "new_content"
    val contentArray = jsonObject.getJSONArray("new_content")
    val contentList = mutableListOf<Content>()

    for (i in 0 until contentArray.length()) {
        val contentObject = contentArray.getJSONObject(i)

        val id = contentObject.getInt("id")
        val contentGeneratorId = contentObject.getInt("content_generator_id")
        val title = contentObject.getString("title")
        val summary = contentObject.getString("summary")
        val url = contentObject.getString("url")
        val topicLabel = contentObject.getString("topic_label")
        val thumbnailUrl = contentObject.optString("thumbnail_url", null) // Nullable, default to null
        val publishedDate = contentObject.getLong("published_date")
        val rankingScore = contentObject.getDouble("ranking_score")
        val score = if (contentObject.has("score")) contentObject.optInt("score", 0) else null // Nullable score
        val clicked = contentObject.getBoolean("clicked")
        val viewed = contentObject.getBoolean("viewed")
        val urlIsLocal = contentObject.getBoolean("url_is_local")
        val contentGeneratorSpecificData = contentObject.optString("content_generator_specific_data", null) // Nullable, default to null
        val lastModifiedTimestamp = contentObject.getLong("last_modified_timestamp")

        val content = Content(
            id = id,
            contentGeneratorId = contentGeneratorId,
            title = title,
            summary = summary,
            url = url,
            topicLabel = topicLabel,
            thumbnailUrl = thumbnailUrl,
            publishedDate = publishedDate,
            rankingScore = rankingScore,
            score = score,
            clicked = clicked,
            viewed = viewed,
            urlIsLocal = urlIsLocal,
            contentGeneratorSpecificData = contentGeneratorSpecificData,
            lastModifiedTimestamp = lastModifiedTimestamp
        )
        contentList.add(content)
    }

    // Parse "newly_viewed_content_ids"
    val newlyViewedContentIdsArray = jsonObject.getJSONArray("newly_viewed_content_ids")
    val newlyViewedContentIds = mutableListOf<Int>()

    for (i in 0 until newlyViewedContentIdsArray.length()) {
        newlyViewedContentIds.add(newlyViewedContentIdsArray.getInt(i))
    }

    val nonViewedContentRankingScoresArray = jsonObject.getJSONArray("non_viewed_content_ranking_scores")
    val contentRankingScoresList = mutableListOf<ContentRanking>()
    for (i in 0 until nonViewedContentRankingScoresArray.length()) {
        val contentRankingObject = nonViewedContentRankingScoresArray.getJSONObject(i)
        val contentId = contentRankingObject.getInt("content_id")
        val rankingScore = contentRankingObject.getDouble("ranking_score")

        val contentRanking = ContentRanking(id = contentId, rankingScore = rankingScore)
        contentRankingScoresList.add(contentRanking)
    }

    // Return the parsed content and newly viewed content ids
    return ParsedContentResponse(
        contentList = contentList,
        newlyViewedContentIds = newlyViewedContentIds,
        contentRankingScoresList = contentRankingScoresList
    )
}
