package com.sih.fitnessmonitor

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageFormat
import android.graphics.Matrix
import android.graphics.Rect
import android.graphics.YuvImage
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Base64
import android.util.Log
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.google.gson.Gson
import com.google.gson.JsonObject
import com.sih.fitnessmonitor.databinding.ActivityStreamBinding
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

class StreamActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityStreamBinding
    private var serverUrl: String = ""
    private var currentMode: String = "squat"
    
    private var cameraProvider: ProcessCameraProvider? = null
    private var imageAnalyzer: ImageAnalysis? = null
    private lateinit var cameraExecutor: ExecutorService
    private var lensFacing = CameraSelector.LENS_FACING_BACK
    
    private val isProcessing = AtomicBoolean(false)
    private val isRunning = AtomicBoolean(false)
    private val consecutiveErrors = java.util.concurrent.atomic.AtomicInteger(0)
    private val mainHandler = Handler(Looper.getMainLooper())
    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(10, java.util.concurrent.TimeUnit.SECONDS)
        .writeTimeout(10, java.util.concurrent.TimeUnit.SECONDS)
        .readTimeout(10, java.util.concurrent.TimeUnit.SECONDS)
        .retryOnConnectionFailure(true)
        .build()
    private val gson = Gson()
    
    companion object {
        private const val TAG = "StreamActivity"
        private const val REQUEST_CODE_PERMISSIONS = 10
        private val REQUIRED_PERMISSIONS = arrayOf(Manifest.permission.CAMERA)
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityStreamBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        serverUrl = intent.getStringExtra("SERVER_URL") ?: "http://10.0.2.2:5000"
        currentMode = intent.getStringExtra("MODE") ?: "squat"
        
        cameraExecutor = Executors.newSingleThreadExecutor()
        
        setupUI()
        
        // Request camera permissions
        if (allPermissionsGranted()) {
            startCamera()
        } else {
            ActivityCompat.requestPermissions(this, REQUIRED_PERMISSIONS, REQUEST_CODE_PERMISSIONS)
        }
    }
    
    private fun allPermissionsGranted() = REQUIRED_PERMISSIONS.all {
        ContextCompat.checkSelfPermission(baseContext, it) == PackageManager.PERMISSION_GRANTED
    }
    
    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_CODE_PERMISSIONS) {
            if (allPermissionsGranted()) {
                startCamera()
            } else {
                Toast.makeText(this, "Camera permission is required", Toast.LENGTH_SHORT).show()
                finish()
            }
        }
    }
    
    private fun setupUI() {
        updateModeUI()
        
        binding.btnSquat.setOnClickListener {
            if (currentMode != "squat") {
                currentMode = "squat"
                updateModeUI()
                resetAnalyzer()
            }
        }
        
        binding.btnJump.setOnClickListener {
            if (currentMode != "jump") {
                currentMode = "jump"
                updateModeUI()
                resetAnalyzer()
            }
        }
        
        binding.btnBack.setOnClickListener {
            finish()
        }
        
        binding.btnSwitchCamera.setOnClickListener {
            switchCamera()
        }
    }
    
    private fun updateModeUI() {
        if (currentMode == "squat") {
            binding.btnSquat.setBackgroundResource(R.drawable.button_active)
            binding.btnJump.setBackgroundResource(R.drawable.button_inactive)
            binding.tvMode.text = "Squat Analysis"
        } else {
            binding.btnSquat.setBackgroundResource(R.drawable.button_inactive)
            binding.btnJump.setBackgroundResource(R.drawable.button_active)
            binding.tvMode.text = "Jump Analysis"
        }
    }
    
    private fun switchCamera() {
        // Toggle between front and back camera
        lensFacing = if (lensFacing == CameraSelector.LENS_FACING_BACK) {
            CameraSelector.LENS_FACING_FRONT
        } else {
            CameraSelector.LENS_FACING_BACK
        }
        
        // Stop current processing and wait for it to complete
        isRunning.set(false)
        isProcessing.set(false)
        
        // Show loading state
        binding.progressBar.visibility = View.VISIBLE
        binding.tvStatus.text = "Switching camera..."
        binding.imageView.setImageBitmap(null)
        binding.previewView.visibility = View.VISIBLE
        
        // Unbind current camera before switching
        try {
            cameraProvider?.unbindAll()
        } catch (e: Exception) {
            Log.e(TAG, "Error unbinding camera: ${e.message}")
        }
        
        // Small delay to ensure camera is fully released before rebinding
        mainHandler.postDelayed({
            startCamera()
            // Show toast
            val cameraName = if (lensFacing == CameraSelector.LENS_FACING_FRONT) "Front" else "Back"
            Toast.makeText(this, "$cameraName camera", Toast.LENGTH_SHORT).show()
        }, 200)
    }
    
    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)
        
        cameraProviderFuture.addListener({
            cameraProvider = cameraProviderFuture.get()
            
            // Preview use case - show camera feed as fallback
            val preview = Preview.Builder()
                .setTargetResolution(android.util.Size(640, 480))
                .build()
                .also {
                    it.setSurfaceProvider(binding.previewView.surfaceProvider)
                }
            
            // Image analysis use case - capture frames for processing
            imageAnalyzer = ImageAnalysis.Builder()
                .setTargetResolution(android.util.Size(640, 480))
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_YUV_420_888)
                .build()
                .also {
                    it.setAnalyzer(cameraExecutor, FrameAnalyzer())
                }
            
            // Select camera based on lensFacing setting
            val cameraSelector = CameraSelector.Builder()
                .requireLensFacing(lensFacing)
                .build()
            
            try {
                cameraProvider?.unbindAll()
                cameraProvider?.bindToLifecycle(
                    this, cameraSelector, preview, imageAnalyzer
                )
                
                isRunning.set(true)
                binding.progressBar.visibility = View.GONE
                binding.tvStatus.text = "Connecting to server..."
                // Show preview as fallback, imageView will overlay when server responds
                binding.previewView.visibility = View.VISIBLE
                binding.imageView.visibility = View.VISIBLE
                
                Log.d(TAG, "Camera started successfully")
                
            } catch (e: Exception) {
                Log.e(TAG, "Camera binding failed", e)
                Toast.makeText(this, "Failed to start camera: ${e.message}", Toast.LENGTH_SHORT).show()
            }
            
        }, ContextCompat.getMainExecutor(this))
    }
    
    private inner class FrameAnalyzer : ImageAnalysis.Analyzer {
        private var frameCount = 0
        private var lastFrameTime = 0L
        private val minFrameInterval = 100L  // ~10 FPS max to not overwhelm server
        
        override fun analyze(image: ImageProxy) {
            val currentTime = System.currentTimeMillis()
            
            // Dynamic rate limiting based on error count
            val errorCount = consecutiveErrors.get()
            val dynamicInterval = if (errorCount >= 5) {
                2000L  // 0.5 FPS when connection is failing
            } else if (errorCount > 0) {
                minFrameInterval * (errorCount + 1)  // Gradually slow down
            } else {
                minFrameInterval
            }
            
            // Rate limiting and state check
            if (!isRunning.get() || isProcessing.get() || 
                (currentTime - lastFrameTime) < dynamicInterval) {
                image.close()
                return
            }
            
            lastFrameTime = currentTime
            isProcessing.set(true)
            frameCount++
            
            try {
                // Convert ImageProxy to Bitmap
                val bitmap = imageProxyToBitmap(image)
                if (bitmap != null) {
                    // Apply rotation and mirroring based on camera facing
                    val rotationDegrees = image.imageInfo.rotationDegrees
                    val needsMirroring = lensFacing == CameraSelector.LENS_FACING_FRONT
                    
                    val transformedBitmap = if (rotationDegrees != 0 || needsMirroring) {
                        val matrix = Matrix().apply {
                            if (rotationDegrees != 0) {
                                postRotate(rotationDegrees.toFloat())
                            }
                            if (needsMirroring) {
                                // Mirror horizontally for front camera
                                postScale(-1f, 1f, bitmap.width / 2f, bitmap.height / 2f)
                            }
                        }
                        val transformed = Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true)
                        if (transformed != bitmap) bitmap.recycle()
                        transformed
                    } else {
                        bitmap
                    }
                    
                    // Send to server for processing
                    sendFrameToServer(transformedBitmap)
                } else {
                    Log.e(TAG, "Failed to convert frame to bitmap")
                    isProcessing.set(false)
                }
            } catch (e: Exception) {
                Log.e(TAG, "Frame analysis error: ${e.message}")
                isProcessing.set(false)
            } finally {
                image.close()
            }
        }
        
        private fun imageProxyToBitmap(image: ImageProxy): Bitmap? {
            return try {
                val yPlane = image.planes[0]
                val uPlane = image.planes[1]
                val vPlane = image.planes[2]

                val yBuffer = yPlane.buffer
                val uBuffer = uPlane.buffer
                val vBuffer = vPlane.buffer

                val imageWidth = image.width
                val imageHeight = image.height

                // Get row strides - crucial for correct conversion
                val yRowStride = yPlane.rowStride
                val uvRowStride = uPlane.rowStride
                val uvPixelStride = uPlane.pixelStride

                // NV21 format: Y plane followed by interleaved VU
                val nv21 = ByteArray(imageWidth * imageHeight * 3 / 2)

                // Copy Y plane, handling row stride padding
                var yIndex = 0
                for (row in 0 until imageHeight) {
                    yBuffer.position(row * yRowStride)
                    yBuffer.get(nv21, yIndex, imageWidth)
                    yIndex += imageWidth
                }

                // Copy UV planes interleaved as VU (NV21 format)
                val uvHeight = imageHeight / 2
                val uvWidth = imageWidth / 2
                var uvIndex = imageWidth * imageHeight

                for (row in 0 until uvHeight) {
                    val uvRowStart = row * uvRowStride
                    for (col in 0 until uvWidth) {
                        val uvOffset = uvRowStart + col * uvPixelStride
                        // NV21 is VUVU... so V first, then U
                        nv21[uvIndex++] = vBuffer.get(uvOffset)
                        nv21[uvIndex++] = uBuffer.get(uvOffset)
                    }
                }

                // Reset buffer positions
                yBuffer.rewind()
                uBuffer.rewind()
                vBuffer.rewind()

                val yuvImage = YuvImage(nv21, ImageFormat.NV21, imageWidth, imageHeight, null)
                val out = ByteArrayOutputStream()
                yuvImage.compressToJpeg(Rect(0, 0, imageWidth, imageHeight), 85, out)
                val imageBytes = out.toByteArray()
                BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.size)
            } catch (e: Exception) {
                Log.e(TAG, "YUV to Bitmap error: ${e.message}", e)
                null
            }
        }
    }
    
    private fun sendFrameToServer(bitmap: Bitmap) {
        val url = "$serverUrl/process_frame"
        
        // Compress bitmap to JPEG (do this before recycling)
        val outputStream = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.JPEG, 75, outputStream)
        
        // Recycle bitmap after encoding is complete
        if (!bitmap.isRecycled) {
            bitmap.recycle()
        }
        
        val imageBytes = outputStream.toByteArray()
        val base64Image = Base64.encodeToString(imageBytes, Base64.NO_WRAP)
        
        Log.d(TAG, "Sending frame to $url, size: ${imageBytes.size} bytes")
        
        // Create JSON request
        val jsonObject = JsonObject().apply {
            addProperty("image", base64Image)
            addProperty("mode", currentMode)
        }
        
        val requestBody = gson.toJson(jsonObject).toRequestBody("application/json".toMediaType())
        
        val request = Request.Builder()
            .url(url)
            .post(requestBody)
            .build()
        
        httpClient.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                Log.e(TAG, "Request failed: ${e.message}")
                val errorCount = consecutiveErrors.incrementAndGet()
                mainHandler.post {
                    if (errorCount >= 5) {
                        binding.tvStatus.text = "Connection Lost - Check Server"
                        // Slow down requests when connection is failing
                    } else {
                        binding.tvStatus.text = "Connection Error (retry ${errorCount})"
                    }
                }
                isProcessing.set(false)
            }
            
            override fun onResponse(call: Call, response: Response) {
                try {
                    val responseBody = response.body?.string()
                    
                    if (response.isSuccessful && responseBody != null) {
                        consecutiveErrors.set(0)  // Reset error counter on success
                        val json = gson.fromJson(responseBody, JsonObject::class.java)
                        val processedImage = json.get("image")?.asString
                        val feedback = json.get("feedback")?.asString ?: ""
                        
                        if (processedImage != null) {
                            // Decode processed image
                            val decodedBytes = Base64.decode(processedImage, Base64.DEFAULT)
                            val processedBitmap = BitmapFactory.decodeByteArray(decodedBytes, 0, decodedBytes.size)
                            
                            if (processedBitmap != null) {
                                mainHandler.post {
                                    if (isRunning.get()) {
                                        // Get old bitmap to recycle after setting new one
                                        val oldBitmap = (binding.imageView.drawable as? android.graphics.drawable.BitmapDrawable)?.bitmap
                                        binding.imageView.setImageBitmap(processedBitmap)
                                        binding.previewView.visibility = View.GONE
                                        binding.tvStatus.text = if (feedback.isNotEmpty()) feedback else "Streaming"
                                        // Recycle old bitmap to prevent memory leaks
                                        oldBitmap?.let { 
                                            if (!it.isRecycled && it != processedBitmap) {
                                                it.recycle()
                                            }
                                        }
                                    } else {
                                        // Activity stopped, recycle the new bitmap
                                        processedBitmap.recycle()
                                    }
                                }
                            }
                        }
                    } else {
                        Log.e(TAG, "Server error: ${response.code}")
                        mainHandler.post {
                            binding.tvStatus.text = "Server Error: ${response.code}"
                        }
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Response parsing error: ${e.message}")
                } finally {
                    isProcessing.set(false)
                }
            }
        })
    }
    
    private fun resetAnalyzer() {
        // Reset the analyzer on the server
        val jsonObject = JsonObject().apply {
            addProperty("mode", currentMode)
        }
        
        val requestBody = gson.toJson(jsonObject).toRequestBody("application/json".toMediaType())
        
        val request = Request.Builder()
            .url("$serverUrl/reset_analyzer")
            .post(requestBody)
            .build()
        
        httpClient.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                Log.e(TAG, "Reset failed: ${e.message}")
            }
            
            override fun onResponse(call: Call, response: Response) {
                response.close()
                Log.d(TAG, "Analyzer reset for mode: $currentMode")
            }
        })
    }
    
    override fun onResume() {
        super.onResume()
        if (allPermissionsGranted() && cameraProvider == null) {
            startCamera()
        }
        isRunning.set(true)
    }
    
    override fun onPause() {
        super.onPause()
        isRunning.set(false)
    }
    
    override fun onDestroy() {
        super.onDestroy()
        isRunning.set(false)
        cameraExecutor.shutdown()
        httpClient.dispatcher.executorService.shutdown()
        httpClient.connectionPool.evictAll()
    }
}
