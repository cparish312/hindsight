package com.connor.hindsight

import android.content.ContentValues
import android.content.Context
import android.database.Cursor
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

class DB(context: Context) :
    SQLiteOpenHelper(context, DATABASE_NAME, null, DATABASE_VERSION) {

    companion object {
        private const val DATABASE_NAME = "hindsight.db"
        private const val DATABASE_VERSION = 1

        private const val TABLE_ANNOTATIONS = "annotations"
        private const val COLUMN_ID = "id"
        private const val COLUMN_TEXT = "text"
        private const val COLUMN_TIMESTAMP = "timestamp"
    }

    override fun onCreate(db: SQLiteDatabase) {
        val CREATE_ANNOTATIONS_TABLE = ("CREATE TABLE " + TABLE_ANNOTATIONS + "("
                + COLUMN_ID + " INTEGER PRIMARY KEY AUTOINCREMENT,"
                + COLUMN_TEXT + " TEXT,"
                + COLUMN_TIMESTAMP + " TIMESTAMP DEFAULT CURRENT_TIMESTAMP" + ")")
        db.execSQL(CREATE_ANNOTATIONS_TABLE)
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        db.execSQL("DROP TABLE IF EXISTS $TABLE_ANNOTATIONS")
        onCreate(db)
    }

    fun addAnnotation(text: String) {
        val db = this.writableDatabase
        val values = ContentValues().apply {
            put(COLUMN_TEXT, text)
        }
        db.insert(TABLE_ANNOTATIONS, null, values)
        db.close()
    }

    fun getAllAnnotations(): Cursor {
        val db = this.readableDatabase
        return db.rawQuery("SELECT * FROM $TABLE_ANNOTATIONS ORDER BY $COLUMN_TIMESTAMP DESC", null)
    }

    fun deleteAnnotation(id: Int) {
        val db = this.writableDatabase
        db.delete(TABLE_ANNOTATIONS, "$COLUMN_ID = ?", arrayOf(id.toString()))
        db.close()
    }
}
