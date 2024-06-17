package com.connor.hindsight.network.interfaces

import okhttp3.MultipartBody
import okhttp3.ResponseBody
import retrofit2.Call
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part

interface ApiService {
    @Multipart
    @POST("upload_image")
    fun uploadFile(@Part file: MultipartBody.Part): Call<ResponseBody>

    @POST("post_query")
    fun postQuery(@Body postData: PostData): Call<ResponseBody>

    @GET("get_queries")
    fun getQueries(@Header("Hightsight-API-Key") apiKey: String): Call<ResponseBody>

    @GET("ping")
    fun pingServer(): Call<ResponseBody>
}

data class PostData(
    val query: String,
    val start_time: Long? = null,
    val end_time:Long? = null
)
