package com.connor.hindsight.models

import android.content.Context
import android.os.Build
import android.util.Log
import android.widget.Toast
import androidx.lifecycle.ViewModel
import androidx.annotation.RequiresApi
import com.connor.hindsight.network.RetrofitClient
import com.connor.hindsight.network.interfaces.ApiService
import com.connor.hindsight.network.interfaces.PostData
import okhttp3.ResponseBody
import java.io.IOException


class PostQueryViewModel : ViewModel() {
    fun postQuery(query: String, startTime: Long?, endTime: Long?, context: Context) {
        Log.d("MainActivity", "postQuery")
        val retrofit = RetrofitClient.instance
        val client = retrofit.create(ApiService::class.java)
        val postData = PostData(query, startTime, endTime)

        client.postQuery(postData).enqueue(object : retrofit2.Callback<ResponseBody> {
            @RequiresApi(Build.VERSION_CODES.O)
            override fun onResponse(
                call: retrofit2.Call<ResponseBody>,
                response: retrofit2.Response<ResponseBody>
            ) {
                if (response.isSuccessful) {
                    Log.d("MainActivity", "Query Post successful: ${response.body()?.string()}")
                    Toast.makeText(context, "Query Post successful!", Toast.LENGTH_SHORT).show()
                } else {
                    Log.e("MainActivity", "Query Post failed: ${response.errorBody()?.string()}")
                }
            }

            override fun onFailure(call: retrofit2.Call<ResponseBody>, t: Throwable) {
                if (t is IOException) {
                    Log.e("MainActivity", "Could not connect to server")
                } else {
                    Log.e(
                        "MainActivity",
                        "Failure in response parsing or serialization: ${t.message}"
                    )
                }
            }
        })
    }
}