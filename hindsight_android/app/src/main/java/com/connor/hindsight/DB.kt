package com.connor.hindsight

import android.content.ContentValues
import android.content.Context
import android.database.Cursor
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import android.util.Log
import com.connor.hindsight.network.interfaces.Location
import com.connor.hindsight.network.interfaces.Annotation
import com.connor.hindsight.obj.Content
import com.connor.hindsight.obj.ContentRanking
import com.connor.hindsight.obj.SyncContent
import com.connor.hindsight.obj.ViewContent

class DB(context: Context) :
    SQLiteOpenHelper(context, DATABASE_NAME, null, DATABASE_VERSION) {

    companion object {
        private const val DATABASE_NAME = "hindsight.db"
        private const val DATABASE_VERSION = 8

        private const val TABLE_ANNOTATIONS = "annotations"
        private const val COLUMN_ID = "id"
        private const val COLUMN_TEXT = "text"
        private const val COLUMN_TIMESTAMP = "timestamp"

        private const val TABLE_LOCATIONS = "locations"
        private const val COLUMN_LATITUDE = "latitude"
        private const val COLUMN_LONGITUDE = "longitude"

        // Content Table
        private const val TABLE_CONTENT = "content"
        private const val COLUMN_CONTENT_ID = "id"
        private const val COLUMN_CONTENT_GENERATOR_ID = "content_generator_id"
        private const val COLUMN_TITLE = "title"
        private const val COLUMN_SUMMARY = "summary"
        private const val COLUMN_URL = "url"
        private const val COLUMN_THUMBNAIL_URL = "thumbnail_url"
        private const val COLUMN_PUBLISHED_DATE = "published_date"
        private const val COLUMN_RANKING_SCORE = "ranking_score"
        private const val COLUMN_SCORE = "score"
        private const val COLUMN_CLICKED = "clicked"
        private const val COLUMN_VIEWED = "viewed"
        private const val COLUMN_URL_IS_LOCAL = "url_is_local"
        private const val COLUMN_CONTENT_GENERATOR_SPECIFIC_DATA = "content_generator_specific_data"
        private const val COLUMN_LAST_MODIFIED_TIMESTAMP = "last_modified_timestamp"
        private const val COLUMN_TOPIC_LABEL = "topic_label"
    }

    override fun onCreate(db: SQLiteDatabase) {
        val CREATE_ANNOTATIONS_TABLE = ("CREATE TABLE IF NOT EXISTS " + TABLE_ANNOTATIONS + "("
                + COLUMN_ID + " INTEGER PRIMARY KEY AUTOINCREMENT,"
                + COLUMN_TEXT + " TEXT,"
                + COLUMN_TIMESTAMP + " INTEGER" + ")")
        db.execSQL(CREATE_ANNOTATIONS_TABLE)

        val CREATE_LOCATIONS_TABLE = ("CREATE TABLE IF NOT EXISTS " + TABLE_LOCATIONS + "("
                + COLUMN_LATITUDE + " DOUBLE,"
                + COLUMN_LONGITUDE + " DOUBLE,"
                + COLUMN_TIMESTAMP + " INTEGER" + ")")
        db.execSQL(CREATE_LOCATIONS_TABLE)

        // Content table creation
        val CREATE_CONTENT_TABLE = ("CREATE TABLE IF NOT EXISTS " + TABLE_CONTENT + "("
                + COLUMN_CONTENT_ID + " INTEGER PRIMARY KEY,"
                + COLUMN_CONTENT_GENERATOR_ID + " INTEGER NOT NULL,"
                + COLUMN_TITLE + " TEXT NOT NULL,"
                + COLUMN_SUMMARY + " TEXT,"
                + COLUMN_URL + " TEXT NOT NULL,"
                + COLUMN_TOPIC_LABEL + " TEXT,"
                + COLUMN_THUMBNAIL_URL + " TEXT,"
                + COLUMN_PUBLISHED_DATE + " INTEGER NOT NULL,"
                + COLUMN_RANKING_SCORE + " REAL NOT NULL,"
                + COLUMN_SCORE + " INTEGER,"
                + COLUMN_CLICKED + " INTEGER DEFAULT 0,"
                + COLUMN_VIEWED + " INTEGER DEFAULT 0,"
                + COLUMN_URL_IS_LOCAL + " INTEGER DEFAULT 0,"
                + COLUMN_CONTENT_GENERATOR_SPECIFIC_DATA + " TEXT,"
                + COLUMN_LAST_MODIFIED_TIMESTAMP + " INTEGER" + ")")
        db.execSQL(CREATE_CONTENT_TABLE)
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
//        db.execSQL("DROP TABLE IF EXISTS $TABLE_ANNOTATIONS")
//        db.execSQL("DROP TABLE IF EXISTS $TABLE_LOCATIONS")
        db.execSQL("DROP TABLE IF EXISTS $TABLE_CONTENT")
        onCreate(db)
    }

    fun addAnnotation(text: String) {
        val db = this.writableDatabase
        val currentTimestamp = System.currentTimeMillis()
        val values = ContentValues().apply {
            put(COLUMN_TEXT, text)
            put(COLUMN_TIMESTAMP, currentTimestamp)
        }
        db.insert(TABLE_ANNOTATIONS, null, values)
        db.close()
    }

    fun convertCursorToAnnotations(cursor: Cursor): List<Annotation> {
        val annotations = mutableListOf<Annotation>()
        if (cursor.moveToFirst()) {
            do {
                val text = cursor.getString(cursor.getColumnIndexOrThrow(COLUMN_TEXT))
                val timestamp = cursor.getLong(cursor.getColumnIndexOrThrow(COLUMN_TIMESTAMP))
                annotations.add(Annotation(text, timestamp))
            } while (cursor.moveToNext())
        }
        cursor.close()
        return annotations
    }

    fun getAnnotations(afterTimestamp: Long? = 0): Cursor {
        val db = this.readableDatabase
        val timestamp = afterTimestamp ?: 0
        return db.rawQuery("SELECT * FROM $TABLE_ANNOTATIONS  WHERE " +
                "$COLUMN_TIMESTAMP > $timestamp ORDER BY $COLUMN_TIMESTAMP DESC",
            null)
    }

    fun deleteAnnotation(id: Int) {
        val db = this.writableDatabase
        db.delete(TABLE_ANNOTATIONS, "$COLUMN_ID = ?", arrayOf(id.toString()))
        db.close()
    }

    fun addLocation(latitude: Double, longitude: Double) {
        val db = this.writableDatabase
        val currentTimestamp = System.currentTimeMillis()
        val values = ContentValues().apply {
            put(COLUMN_LATITUDE, latitude)
            put(COLUMN_LONGITUDE, longitude)
            put(COLUMN_TIMESTAMP, currentTimestamp)
        }
        db.insert(TABLE_LOCATIONS, null, values)
        Log.d("DB", "Location added: $latitude, $longitude")
        db.close()
    }

    fun convertCursorToLocations(cursor: Cursor): List<Location> {
        val locations = mutableListOf<Location>()
        if (cursor.moveToFirst()) {
            do {
                val latitude = cursor.getDouble(cursor.getColumnIndexOrThrow(COLUMN_LATITUDE))
                val longitude = cursor.getDouble(cursor.getColumnIndexOrThrow(COLUMN_LONGITUDE))
                val timestamp = cursor.getLong(cursor.getColumnIndexOrThrow(COLUMN_TIMESTAMP))
                locations.add(Location(latitude, longitude, timestamp))
            } while (cursor.moveToNext())
        }
        cursor.close()
        return locations
    }

    fun getLocations(afterTimestamp: Long? = 0): Cursor {
        val db = this.readableDatabase
        val timestamp = afterTimestamp ?: 0
        return db.rawQuery("SELECT * FROM $TABLE_LOCATIONS WHERE " +
                "$COLUMN_TIMESTAMP > $timestamp ORDER BY $COLUMN_TIMESTAMP DESC", null)
    }

    fun addContentBatch(contentList: List<Content>) {
        val db = this.writableDatabase
        db.beginTransaction()  // Start a transaction
        try {
            val values = ContentValues()
            for (content in contentList) {
                values.apply {
                    clear()  // Reset content values for each insert
                    put(COLUMN_CONTENT_ID, content.id)
                    put(COLUMN_CONTENT_GENERATOR_ID, content.contentGeneratorId)
                    put(COLUMN_TITLE, content.title)
                    put(COLUMN_SUMMARY, content.summary)
                    put(COLUMN_URL, content.url)
                    put(COLUMN_TOPIC_LABEL, content.topicLabel)
                    put(COLUMN_THUMBNAIL_URL, content.thumbnailUrl)
                    put(COLUMN_PUBLISHED_DATE, content.publishedDate)
                    put(COLUMN_RANKING_SCORE, content.rankingScore)
                    put(COLUMN_SCORE, content.score)
                    put(COLUMN_CLICKED, if (content.clicked) 1 else 0)
                    put(COLUMN_VIEWED, if (content.viewed) 1 else 0)
                    put(COLUMN_URL_IS_LOCAL, if (content.urlIsLocal) 1 else 0)
                    put(COLUMN_CONTENT_GENERATOR_SPECIFIC_DATA, content.contentGeneratorSpecificData)
                    put(COLUMN_LAST_MODIFIED_TIMESTAMP, System.currentTimeMillis())
                }

                db.insert(TABLE_CONTENT, null, values)
            }
            db.setTransactionSuccessful()  // Mark transaction as successful
        } catch (e: Exception) {
            Log.e("DB", "Error inserting batch content", e)
        } finally {
            db.endTransaction()  // End the transaction
            db.close()
        }
    }

    fun getContent(afterTimestamp: Long? = 0, nonViewed: Boolean = false): Cursor {
        val db = this.readableDatabase
        val timestamp = afterTimestamp ?: 0
        val nonViewedClause = if (nonViewed) " AND $COLUMN_VIEWED = 0" else ""
        return db.rawQuery("SELECT * FROM $TABLE_CONTENT WHERE " +
                "$COLUMN_LAST_MODIFIED_TIMESTAMP > $timestamp$nonViewedClause ORDER BY " +
                "$COLUMN_RANKING_SCORE DESC", null)
    }

    fun convertCursorToSyncContent(cursor: Cursor): List<SyncContent> {
        val contentList = mutableListOf<SyncContent>()
        if (cursor.moveToFirst()) {
            do {
                val id = cursor.getInt(cursor.getColumnIndexOrThrow(COLUMN_CONTENT_ID))
                val lastModifiedTimestamp = cursor.getLong(cursor.getColumnIndexOrThrow(COLUMN_LAST_MODIFIED_TIMESTAMP))
                val viewed = cursor.getInt(cursor.getColumnIndexOrThrow(COLUMN_VIEWED)) == 1
                val score = cursor.getInt(cursor.getColumnIndexOrThrow(COLUMN_SCORE))
                val clicked = cursor.getInt(cursor.getColumnIndexOrThrow(COLUMN_CLICKED)) == 1

                contentList.add(
                    SyncContent(id=id, lastModifiedTimestamp=lastModifiedTimestamp,
                    viewed=viewed, score=score, clicked=clicked)
                )
            } while (cursor.moveToNext())
        }
        cursor.close()
        return contentList
    }

    fun convertCursorToViewContent(cursor: Cursor): List<ViewContent> {
        val contentList = mutableListOf<ViewContent>()
        if (cursor.moveToFirst()) {
            do {
                val id = cursor.getInt(cursor.getColumnIndexOrThrow(COLUMN_CONTENT_ID))
                val title = cursor.getString(cursor.getColumnIndexOrThrow(COLUMN_TITLE))
                val rawSummary = cursor.getString(cursor.getColumnIndexOrThrow(COLUMN_SUMMARY))
                val summary = if (rawSummary == "null") null else rawSummary
                val url = cursor.getString(cursor.getColumnIndexOrThrow(COLUMN_URL))
                val topicLabel = cursor.getString(cursor.getColumnIndexOrThrow(COLUMN_TOPIC_LABEL))
                val rawThumbnailUrl = cursor.getString(cursor.getColumnIndexOrThrow(COLUMN_THUMBNAIL_URL))
                val thumbnailUrl = if (rawThumbnailUrl == "null") null else rawThumbnailUrl
                val score = cursor.getInt(cursor.getColumnIndexOrThrow(COLUMN_SCORE))
                val rankingScore = cursor.getDouble(cursor.getColumnIndexOrThrow(COLUMN_RANKING_SCORE))


                contentList.add(
                    ViewContent(id=id, title=title, summary=summary, thumbnailUrl=thumbnailUrl,
                        url=url, score=score, topicLabel = topicLabel, rankingScore=rankingScore)
                )
            } while (cursor.moveToNext())
        }
        cursor.close()
        return contentList
    }

    fun getMaxContentId(): Int {
        val db = this.readableDatabase
        val cursor = db.rawQuery("SELECT MAX($COLUMN_CONTENT_ID) AS max_id FROM $TABLE_CONTENT", null)

        var maxId = -1  // Default value if there are no rows in the table
        if (cursor.moveToFirst()) {
            maxId = cursor.getInt(cursor.getColumnIndexOrThrow("max_id"))
        }
        cursor.close()
        return maxId
    }

    fun markContentAsViewed(contentIds: List<Int>) {
        val db = this.writableDatabase
        db.beginTransaction()  // Start a transaction for batch updates
        try {
            for (contentId in contentIds) {
                // Query to check if the content is already viewed
                val cursor = db.rawQuery(
                    "SELECT $COLUMN_VIEWED FROM $TABLE_CONTENT WHERE $COLUMN_CONTENT_ID = ?",
                    arrayOf(contentId.toString())
                )

                if (cursor.moveToFirst()) {
                    val isViewed = cursor.getInt(cursor.getColumnIndexOrThrow(COLUMN_VIEWED)) == 1
                    if (!isViewed) {
                        // If the content is not viewed, update it to viewed
                        val values = ContentValues().apply {
                            put(COLUMN_VIEWED, 1)  // Mark as viewed
                            put(COLUMN_LAST_MODIFIED_TIMESTAMP, System.currentTimeMillis())  // Update the last modified timestamp
                        }
                        db.update(TABLE_CONTENT, values, "$COLUMN_CONTENT_ID = ?", arrayOf(contentId.toString()))
                    }
                }
                cursor.close()  // Close the cursor after each query
            }
            db.setTransactionSuccessful()  // Mark the transaction as successful
        } catch (e: Exception) {
            Log.e("DB", "Error updating content viewed status", e)
        } finally {
            db.endTransaction()  // End the transaction
            db.close()  // Close the database connection
        }
    }

    fun markContentAsClicked(contentIds: List<Int>) {
        val db = this.writableDatabase
        db.beginTransaction()  // Start a transaction for batch updates
        try {
            for (contentId in contentIds) {
                // Query to check if the content is already viewed
                val cursor = db.rawQuery(
                    "SELECT $COLUMN_CLICKED FROM $TABLE_CONTENT WHERE $COLUMN_CONTENT_ID = ?",
                    arrayOf(contentId.toString())
                )

                if (cursor.moveToFirst()) {
                    val isClicked = cursor.getInt(cursor.getColumnIndexOrThrow(COLUMN_CLICKED)) == 1
                    if (!isClicked) {
                        // If the content is not clicked, update it to clicked
                        val values = ContentValues().apply {
                            put(COLUMN_CLICKED, 1)  // Mark as viewed
                            put(COLUMN_LAST_MODIFIED_TIMESTAMP, System.currentTimeMillis())  // Update the last modified timestamp
                        }
                        db.update(TABLE_CONTENT, values, "$COLUMN_CONTENT_ID = ?", arrayOf(contentId.toString()))
                    }
                }
                cursor.close()  // Close the cursor after each query
            }
            db.setTransactionSuccessful()  // Mark the transaction as successful
        } catch (e: Exception) {
            Log.e("DB", "Error updating content clicked status", e)
        } finally {
            db.endTransaction()  // End the transaction
            db.close()  // Close the database connection
        }
    }

    fun updateContentScore(contentId: Int, newScore: Int) {
        val db = this.writableDatabase
        val contentValues = ContentValues().apply {
            put(COLUMN_SCORE, newScore)
            put(COLUMN_LAST_MODIFIED_TIMESTAMP, System.currentTimeMillis())
        }
        db.update(TABLE_CONTENT, contentValues, "$COLUMN_CONTENT_ID = ?", arrayOf(contentId.toString()))
        db.close()
    }

    fun updateContentRankingScores(contentRankingList: List<ContentRanking>) {
        val db = this.writableDatabase
        try {
            db.beginTransaction()
            for (contentRanking in contentRankingList) {
                val contentValues = ContentValues().apply {
                    put(COLUMN_RANKING_SCORE, contentRanking.rankingScore)
                }
                db.update(TABLE_CONTENT, contentValues, "$COLUMN_CONTENT_ID = ?", arrayOf(contentRanking.id.toString()))
            }
            db.setTransactionSuccessful()
        } finally {
            db.endTransaction()
            db.close()
        }
    }
}
