package com.connor.hindsight.network.interfaces

import okhttp3.MultipartBody
import okhttp3.ResponseBody
import retrofit2.Call
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Query

interface ApiService {
    @Multipart
    @POST("upload_image")
    fun uploadFile(@Part file: MultipartBody.Part): Call<ResponseBody>

    @POST("post_query")
    fun postQuery(@Body postData: PostData): Call<ResponseBody>

    @GET("get_queries")
    fun getQueries(): Call<ResponseBody>

    @GET("get_last_timestamp")
    suspend fun getLastTimestamp(@Query("table") tableName: String): Response<TimestampResponse>

    @POST("sync_db")
    suspend fun syncDB(@Body syncDBDate: SyncDBData): Response<ResponseBody>

    @GET("ping")
    fun pingServer(): Call<ResponseBody>
}

data class PostData(
    val query: String,
    val context_start_timestamp: Long? = null,
    val context_end_timestamp:Long? = null
)

data class SyncDBData(
    val annotations: List<Annotation>,
    val locations: List<Location>
)

data class Annotation(
    val text: String,
    val timestamp: Long
)

data class Location(
    val latitude: Double,
    val longitude: Double,
    val timestamp: Long
)

data class TimestampResponse(
    val last_timestamp: Long?
)