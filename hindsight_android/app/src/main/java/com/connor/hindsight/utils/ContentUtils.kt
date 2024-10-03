package com.connor.hindsight.utils

import com.connor.hindsight.obj.Content
import org.json.JSONArray
import org.json.JSONObject

data class ParsedContentResponse(
    val contentList: List<Content>,
    val newlyViewedContentIds: List<Int>
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
        val url = contentObject.getString("url")
        val thumbnailUrl = contentObject.optString("thumbnail_url", null) // Nullable, default to null
        val publishedDate = contentObject.getLong("published_date")
        val rankingScore = contentObject.getDouble("ranking_score").toFloat()
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
            url = url,
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

    // Return the parsed content and newly viewed content ids
    return ParsedContentResponse(
        contentList = contentList,
        newlyViewedContentIds = newlyViewedContentIds
    )
}
