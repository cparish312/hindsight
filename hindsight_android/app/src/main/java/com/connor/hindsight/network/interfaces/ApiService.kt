import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.ResponseBody
import retrofit2.Call
import retrofit2.http.*

interface ApiService {
    @Multipart
    @POST("upload_image")
    fun uploadFile(@Part file: MultipartBody.Part): Call<ResponseBody>

    @POST("data")
    fun uploadJson(@Body body: RequestBody): Call<ResponseBody>
}