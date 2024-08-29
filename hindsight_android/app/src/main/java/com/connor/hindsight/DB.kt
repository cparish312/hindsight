package com.connor.hindsight

import android.content.ContentValues
import android.content.Context
import android.database.Cursor
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import android.util.Log
import com.connor.hindsight.network.interfaces.Location
import com.connor.hindsight.network.interfaces.Annotation

class DB(context: Context) :
    SQLiteOpenHelper(context, DATABASE_NAME, null, DATABASE_VERSION) {

    companion object {
        private const val DATABASE_NAME = "hindsight.db"
        private const val DATABASE_VERSION = 3

        private const val TABLE_ANNOTATIONS = "annotations"
        private const val COLUMN_ID = "id"
        private const val COLUMN_TEXT = "text"
        private const val COLUMN_TIMESTAMP = "timestamp"

        private const val TABLE_LOCATIONS = "locations"
        private const val COLUMN_LATITUDE = "latitude"
        private const val COLUMN_LONGITUDE = "longitude"
    }

    override fun onCreate(db: SQLiteDatabase) {
        val CREATE_ANNOTATIONS_TABLE = ("CREATE TABLE " + TABLE_ANNOTATIONS + "("
                + COLUMN_ID + " INTEGER PRIMARY KEY AUTOINCREMENT,"
                + COLUMN_TEXT + " TEXT,"
                + COLUMN_TIMESTAMP + " INTEGER" + ")")
        db.execSQL(CREATE_ANNOTATIONS_TABLE)

        val CREATE_LOCATIONS_TABLE = ("CREATE TABLE " + TABLE_LOCATIONS + "("
                + COLUMN_LATITUDE + " DOUBLE,"
                + COLUMN_LONGITUDE + " DOUBLE,"
                + COLUMN_TIMESTAMP + " INTEGER" + ")")
        db.execSQL(CREATE_LOCATIONS_TABLE)
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
//        db.execSQL("DROP TABLE IF EXISTS $TABLE_ANNOTATIONS")
//        db.execSQL("DROP TABLE IF EXISTS $TABLE_LOCATIONS")
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

    fun getAnnotations(afterTimestamp: Int? = 0): Cursor {
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

    fun getLocations(afterTimestamp: Int? = 0): Cursor {
        val db = this.readableDatabase
        val timestamp = afterTimestamp ?: 0
        return db.rawQuery("SELECT * FROM $TABLE_LOCATIONS WHERE " +
                "$COLUMN_TIMESTAMP > $timestamp ORDER BY $COLUMN_TIMESTAMP DESC", null)
    }
}
