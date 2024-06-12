package com.connor.hindsight.network.interfaces

import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.ResponseBody
import retrofit2.Call
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part

interface ApiService {
    @Multipart
    @POST("upload_image")
    fun uploadFile(@Part file: MultipartBody.Part): Call<ResponseBody>

    @POST("data")
    fun uploadJson(@Body body: RequestBody): Call<ResponseBody>

    @GET("ping")
    fun pingServer(): Call<ResponseBody>
}
