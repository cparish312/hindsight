package com.connor.hindsight.network

import java.util.concurrent.TimeUnit
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object RetrofitClient {
    private const val BASE_URL = "https://192.168.1.220:6000/"

    fun getInstance(baseUrl: String): Retrofit
    {
        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BASIC
        }

        val client = OkHttpClient.Builder()
            .connectTimeout(1, TimeUnit.SECONDS) // Set the connection timeout
            .readTimeout(30, TimeUnit.SECONDS) // Set the read timeout
            .writeTimeout(30, TimeUnit.SECONDS) // Set the write timeout
            .addInterceptor(logging)
            .build()

        return Retrofit.Builder()
            .baseUrl(baseUrl)
            .addConverterFactory(GsonConverterFactory.create())
            .client(client)
            .build()
    }
}
