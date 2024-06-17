package com.connor.hindsight.models

import android.content.Context
import android.util.Log
import android.widget.Toast
import androidx.lifecycle.ViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import com.connor.hindsight.network.RetrofitClient
import com.connor.hindsight.network.interfaces.ApiService
import com.connor.hindsight.network.interfaces.PostData
import com.connor.hindsight.utils.Preferences
import okhttp3.ResponseBody
import org.json.JSONArray


class QueryViewModel : ViewModel() {
    private val _queries = MutableLiveData<List<String>>()
    val queries: LiveData<List<String>> = _queries
    private val primaryUrl: String = Preferences.prefs.getString(
            Preferences.localurl,
            ""
        ).toString()
    private val fallbackUrl: String = Preferences.prefs.getString(
        Preferences.interneturl,
        ""
    ).toString()

    fun postQuery(query: String, startTime: Long?, endTime: Long?, context: Context) {
        makePostRequest(primaryUrl, query, startTime, endTime, context)
    }

    private fun makePostRequest(baseUrl: String, query: String, startTime: Long?, endTime: Long?, context: Context) {
        val retrofit = RetrofitClient.getInstance(baseUrl)
        val client = retrofit.create(ApiService::class.java)
        val postData = PostData(query, startTime, endTime)

        client.postQuery(postData).enqueue(object : retrofit2.Callback<ResponseBody> {
            override fun onResponse(call: retrofit2.Call<ResponseBody>, response: retrofit2.Response<ResponseBody>) {
                if (response.isSuccessful) {
                    Toast.makeText(context, "Query Post successful!", Toast.LENGTH_SHORT).show()
                } else {
                    if (baseUrl == primaryUrl) {
                        makePostRequest(fallbackUrl, query, startTime, endTime, context) // Try the fallback URL
                    } else {
                        Log.e("QueryViewModel", "Query Post failed at both servers: ${response.errorBody()?.string()}")
                    }
                }
            }

            override fun onFailure(call: retrofit2.Call<ResponseBody>, t: Throwable) {
                if (baseUrl == primaryUrl) {
                    makePostRequest(fallbackUrl, query, startTime, endTime, context) // Try the fallback URL
                } else {
                    Log.e("QueryViewModel", "Error connecting to both servers: ${t.message}")
                }
            }
        })
    }

    fun fetchQueries() {
        fetchWithUrl(primaryUrl)
    }

    private fun fetchWithUrl(baseUrl: String) {
        val retrofit = RetrofitClient.getInstance(baseUrl)
        val client = retrofit.create(ApiService::class.java)

        client.getQueries().enqueue(object : retrofit2.Callback<ResponseBody> {
            override fun onResponse(call: retrofit2.Call<ResponseBody>, response: retrofit2.Response<ResponseBody>) {
                if (response.isSuccessful) {
                    val resultString = response.body()?.string() ?: ""
                    val queriesList: List<String> = parseJsonToQueryList(resultString)
                    _queries.postValue(queriesList)
                } else {
                    if (baseUrl == primaryUrl) {
                        fetchWithUrl(fallbackUrl) // Retry with the fallback URL
                    } else {
                        Log.e("QueryViewModel", "Failed to fetch queries at both servers")
                    }
                }
            }

            override fun onFailure(call: retrofit2.Call<ResponseBody>, t: Throwable) {
                if (baseUrl == primaryUrl) {
                    fetchWithUrl(fallbackUrl) // Retry with the fallback URL
                } else {
                    Log.e("QueryViewModel", "Error connecting to both servers: ${t.message}")
                }
            }
        })
    }

    private fun parseJsonToQueryList(json: String): List<String> {
        val jsonArray = JSONArray(json)
        val resultList = mutableListOf<String>()

        for (i in 0 until jsonArray.length()) {
            val jsonObject = jsonArray.getJSONObject(i)
            val query = jsonObject.getString("query")
            val result = jsonObject.getString("result")
            resultList.add("Query: $query\nResult: $result")
        }
        return resultList
    }
}