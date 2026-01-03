package com.mdxvision

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.os.Bundle
import android.util.Base64
import android.util.Log
import android.widget.Button
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import java.io.ByteArrayOutputStream
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * MDx Vision - Image Capture Activity
 * Feature #70: Medical Image Recognition
 *
 * Captures medical images (wounds, rashes, X-rays) for Claude Vision analysis.
 * Returns base64-encoded JPEG image via Intent.
 */
class ImageCaptureActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "MDxImageCapture"
        private const val CAMERA_PERMISSION_CODE = 1003

        // Intent extras
        const val EXTRA_IMAGE_BASE64 = "image_base64"
        const val EXTRA_MEDIA_TYPE = "media_type"
        const val EXTRA_ANALYSIS_CONTEXT = "analysis_context"

        // Input extras (from MainActivity)
        const val INPUT_ANALYSIS_CONTEXT = "input_context"
    }

    private lateinit var cameraExecutor: ExecutorService
    private lateinit var previewView: PreviewView
    private lateinit var statusText: TextView
    private lateinit var instructionText: TextView
    private lateinit var captureButton: Button

    private var imageCapture: ImageCapture? = null
    private var analysisContext: String? = null
    private var isCapturing = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Get analysis context from intent
        analysisContext = intent.getStringExtra(INPUT_ANALYSIS_CONTEXT)

        setupUI()
        cameraExecutor = Executors.newSingleThreadExecutor()

        if (hasCameraPermission()) {
            startCamera()
        } else {
            requestCameraPermission()
        }
    }

    private fun setupUI() {
        val layout = FrameLayout(this).apply {
            setBackgroundColor(0xFF000000.toInt())
        }

        // Camera preview - full screen
        previewView = PreviewView(this).apply {
            layoutParams = FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
            )
        }
        layout.addView(previewView)

        // Top overlay with instructions
        val topOverlay = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                gravity = android.view.Gravity.TOP
            }
            setBackgroundColor(0x99000000.toInt())
            setPadding(32, 32, 32, 32)
        }

        // Title based on context
        val titleText = when (analysisContext) {
            "wound" -> "Capture Wound Image"
            "rash" -> "Capture Skin/Rash Image"
            "xray" -> "Capture X-Ray Image"
            else -> "Capture Medical Image"
        }

        statusText = TextView(this).apply {
            text = titleText
            textSize = 24f
            setTextColor(0xFFFFFFFF.toInt())
        }
        topOverlay.addView(statusText)

        // Instruction text based on context
        val instructionMessage = when (analysisContext) {
            "wound" -> "Center the wound in frame. Good lighting helps analysis."
            "rash" -> "Center the affected skin area. Include clear boundaries."
            "xray" -> "Capture the X-ray image straight-on if possible."
            else -> "Center the area of interest. Tap CAPTURE when ready."
        }

        instructionText = TextView(this).apply {
            text = instructionMessage
            textSize = 16f
            setTextColor(0xFFCCCCCC.toInt())
            setPadding(0, 8, 0, 0)
        }
        topOverlay.addView(instructionText)

        layout.addView(topOverlay)

        // Bottom button bar
        val bottomBar = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            layoutParams = FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                gravity = android.view.Gravity.BOTTOM
            }
            setBackgroundColor(0x99000000.toInt())
            setPadding(32, 24, 32, 24)
            gravity = android.view.Gravity.CENTER
        }

        // Cancel button
        val cancelButton = Button(this).apply {
            text = "Cancel"
            layoutParams = LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.WRAP_CONTENT,
                1f
            ).apply {
                marginEnd = 16
            }
            setOnClickListener {
                setResult(RESULT_CANCELED)
                finish()
            }
        }
        bottomBar.addView(cancelButton)

        // Capture button - prominent
        captureButton = Button(this).apply {
            text = "CAPTURE"
            textSize = 18f
            layoutParams = LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.WRAP_CONTENT,
                2f
            )
            setOnClickListener { captureImage() }
        }
        bottomBar.addView(captureButton)

        layout.addView(bottomBar)

        // Make preview tappable for capture
        previewView.setOnClickListener { captureImage() }

        setContentView(layout)
    }

    private fun hasCameraPermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            this, Manifest.permission.CAMERA
        ) == PackageManager.PERMISSION_GRANTED
    }

    private fun requestCameraPermission() {
        ActivityCompat.requestPermissions(
            this,
            arrayOf(Manifest.permission.CAMERA),
            CAMERA_PERMISSION_CODE
        )
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == CAMERA_PERMISSION_CODE) {
            if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                startCamera()
            } else {
                Toast.makeText(this, "Camera permission required", Toast.LENGTH_SHORT).show()
                finish()
            }
        }
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)

        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()

            // Preview use case
            val preview = Preview.Builder()
                .build()
                .also {
                    it.setSurfaceProvider(previewView.surfaceProvider)
                }

            // ImageCapture use case - high quality for medical images
            imageCapture = ImageCapture.Builder()
                .setCaptureMode(ImageCapture.CAPTURE_MODE_MAXIMIZE_QUALITY)
                .setTargetRotation(windowManager.defaultDisplay.rotation)
                .build()

            // Select back camera
            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA

            try {
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(
                    this, cameraSelector, preview, imageCapture
                )
                Log.d(TAG, "Camera started successfully")
            } catch (e: Exception) {
                Log.e(TAG, "Camera binding failed: ${e.message}")
                Toast.makeText(this, "Camera error: ${e.message}", Toast.LENGTH_SHORT).show()
            }

        }, ContextCompat.getMainExecutor(this))
    }

    private fun captureImage() {
        val imageCapture = imageCapture ?: return

        if (isCapturing) return
        isCapturing = true

        runOnUiThread {
            statusText.text = "Capturing..."
            captureButton.isEnabled = false
        }

        // Capture to memory (not file)
        imageCapture.takePicture(
            ContextCompat.getMainExecutor(this),
            object : ImageCapture.OnImageCapturedCallback() {
                override fun onCaptureSuccess(imageProxy: ImageProxy) {
                    Log.d(TAG, "Image captured successfully")

                    try {
                        // Convert to bitmap
                        val bitmap = imageProxyToBitmap(imageProxy)
                        imageProxy.close()

                        if (bitmap != null) {
                            // Compress and encode to base64
                            val base64Image = bitmapToBase64(bitmap, 85)
                            Log.d(TAG, "Image encoded, base64 length: ${base64Image.length}")

                            // Return result
                            val resultIntent = Intent().apply {
                                putExtra(EXTRA_IMAGE_BASE64, base64Image)
                                putExtra(EXTRA_MEDIA_TYPE, "image/jpeg")
                                putExtra(EXTRA_ANALYSIS_CONTEXT, analysisContext ?: "general")
                            }
                            setResult(RESULT_OK, resultIntent)

                            runOnUiThread {
                                statusText.text = "Image Captured!"
                                Toast.makeText(this@ImageCaptureActivity,
                                    "Image captured for analysis", Toast.LENGTH_SHORT).show()
                            }

                            // Short delay to show success
                            previewView.postDelayed({
                                finish()
                            }, 300)
                        } else {
                            onError(ImageCaptureException(
                                ImageCapture.ERROR_UNKNOWN,
                                "Failed to convert image",
                                null
                            ))
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "Error processing image: ${e.message}")
                        onError(ImageCaptureException(
                            ImageCapture.ERROR_UNKNOWN,
                            "Error processing image: ${e.message}",
                            e
                        ))
                    }
                }

                override fun onError(exception: ImageCaptureException) {
                    Log.e(TAG, "Image capture failed: ${exception.message}")
                    isCapturing = false

                    runOnUiThread {
                        statusText.text = "Capture Failed"
                        captureButton.isEnabled = true
                        Toast.makeText(
                            this@ImageCaptureActivity,
                            "Capture failed: ${exception.message}",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                }
            }
        )
    }

    /**
     * Convert ImageProxy to Bitmap
     */
    private fun imageProxyToBitmap(imageProxy: ImageProxy): Bitmap? {
        val buffer = imageProxy.planes[0].buffer
        val bytes = ByteArray(buffer.remaining())
        buffer.get(bytes)

        val bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)

        // Rotate if needed based on rotation degrees
        val rotationDegrees = imageProxy.imageInfo.rotationDegrees
        return if (rotationDegrees != 0) {
            val matrix = Matrix().apply { postRotate(rotationDegrees.toFloat()) }
            Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true)
        } else {
            bitmap
        }
    }

    /**
     * Convert Bitmap to base64 JPEG string
     */
    private fun bitmapToBase64(bitmap: Bitmap, quality: Int = 85): String {
        val byteArrayOutputStream = ByteArrayOutputStream()

        // Resize if too large (max 2048px on longest edge for API efficiency)
        val maxDimension = 2048
        val scaledBitmap = if (bitmap.width > maxDimension || bitmap.height > maxDimension) {
            val scale = maxDimension.toFloat() / maxOf(bitmap.width, bitmap.height)
            Bitmap.createScaledBitmap(
                bitmap,
                (bitmap.width * scale).toInt(),
                (bitmap.height * scale).toInt(),
                true
            )
        } else {
            bitmap
        }

        scaledBitmap.compress(Bitmap.CompressFormat.JPEG, quality, byteArrayOutputStream)
        val byteArray = byteArrayOutputStream.toByteArray()
        return Base64.encodeToString(byteArray, Base64.NO_WRAP)
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
    }
}
