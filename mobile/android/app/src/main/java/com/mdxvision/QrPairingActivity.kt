package com.mdxvision

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.util.Log
import android.util.Size
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import org.json.JSONObject
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * MDx Vision - QR Code Scanner for Device Pairing
 *
 * Scans QR code from web dashboard to pair glasses with clinician account.
 *
 * QR Format: { "action": "pair_device", "token": "xxx", "api_url": "https://..." }
 */
class QrPairingActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "MDxQRPairing"
        private const val CAMERA_PERMISSION_CODE = 1004
        const val EXTRA_PAIRING_TOKEN = "pairing_token"
        const val EXTRA_API_URL = "api_url"
        const val EXTRA_SUCCESS = "pairing_success"
        const val EXTRA_CLINICIAN_NAME = "clinician_name"
        const val EXTRA_ERROR = "error_message"
    }

    private lateinit var cameraExecutor: ExecutorService
    private lateinit var previewView: PreviewView
    private lateinit var statusText: TextView
    private lateinit var instructionText: TextView

    private var isScanning = true
    private val barcodeScanner = BarcodeScanning.getClient()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setupUI()

        cameraExecutor = Executors.newSingleThreadExecutor()

        if (hasCameraPermission()) {
            startCamera()
        } else {
            requestCameraPermission()
        }
    }

    private fun setupUI() {
        val layout = android.widget.FrameLayout(this).apply {
            setBackgroundColor(0xFF000000.toInt())
        }

        // Camera preview
        previewView = PreviewView(this).apply {
            layoutParams = android.widget.FrameLayout.LayoutParams(
                android.widget.FrameLayout.LayoutParams.MATCH_PARENT,
                android.widget.FrameLayout.LayoutParams.MATCH_PARENT
            )
        }
        layout.addView(previewView)

        // Overlay layout
        val overlayLayout = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            layoutParams = android.widget.FrameLayout.LayoutParams(
                android.widget.FrameLayout.LayoutParams.MATCH_PARENT,
                android.widget.FrameLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                gravity = android.view.Gravity.TOP
            }
            setBackgroundColor(0x99000000.toInt())
            setPadding(32, 32, 32, 32)
        }

        statusText = TextView(this).apply {
            text = "Pair Device"
            textSize = 24f
            setTextColor(0xFFFFFFFF.toInt())
        }
        overlayLayout.addView(statusText)

        instructionText = TextView(this).apply {
            text = "Scan the QR code from your Minerva dashboard"
            textSize = 16f
            setTextColor(0xFFCCCCCC.toInt())
            setPadding(0, 8, 0, 0)
        }
        overlayLayout.addView(instructionText)

        layout.addView(overlayLayout)

        // Scan frame overlay (visual guide)
        val scanFrame = android.view.View(this).apply {
            layoutParams = android.widget.FrameLayout.LayoutParams(400, 400).apply {
                gravity = android.view.Gravity.CENTER
            }
            setBackgroundResource(android.R.drawable.ic_menu_crop)
        }
        layout.addView(scanFrame)

        // Cancel button at bottom
        val cancelButton = android.widget.Button(this).apply {
            text = "Cancel"
            layoutParams = android.widget.FrameLayout.LayoutParams(
                android.widget.FrameLayout.LayoutParams.WRAP_CONTENT,
                android.widget.FrameLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                gravity = android.view.Gravity.BOTTOM or android.view.Gravity.CENTER_HORIZONTAL
                bottomMargin = 64
            }
            setOnClickListener { finish() }
        }
        layout.addView(cancelButton)

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
                Toast.makeText(this, "Camera permission required for pairing", Toast.LENGTH_SHORT).show()
                finish()
            }
        }
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)

        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()

            // Preview
            val preview = Preview.Builder()
                .build()
                .also {
                    it.setSurfaceProvider(previewView.surfaceProvider)
                }

            // Image analysis for QR scanning
            val imageAnalyzer = ImageAnalysis.Builder()
                .setTargetResolution(Size(1280, 720))
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
                .also {
                    it.setAnalyzer(cameraExecutor, QrAnalyzer { barcode ->
                        onQrCodeDetected(barcode)
                    })
                }

            // Select back camera
            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA

            try {
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(
                    this, cameraSelector, preview, imageAnalyzer
                )
                Log.d(TAG, "Camera started successfully")
            } catch (e: Exception) {
                Log.e(TAG, "Camera binding failed: ${e.message}")
            }

        }, ContextCompat.getMainExecutor(this))
    }

    private fun onQrCodeDetected(barcode: Barcode) {
        if (!isScanning) return

        val rawValue = barcode.rawValue ?: return
        Log.d(TAG, "QR detected: $rawValue")

        // Only process QR codes (not other barcode types)
        if (barcode.format != Barcode.FORMAT_QR_CODE) {
            Log.d(TAG, "Not a QR code, ignoring")
            return
        }

        // Parse the QR data
        try {
            val qrData = JSONObject(rawValue)

            // Verify it's a pairing QR
            if (qrData.optString("action") != "pair_device") {
                Log.d(TAG, "Not a pairing QR code")
                runOnUiThread {
                    instructionText.text = "Invalid QR code. Scan the pairing QR from your dashboard."
                }
                return
            }

            isScanning = false

            val token = qrData.getString("token")
            val apiUrl = qrData.optString("api_url", "")

            runOnUiThread {
                statusText.text = "QR Detected!"
                instructionText.text = "Pairing in progress..."
            }

            Log.d(TAG, "Pairing token: $token")

            // Return result to MainActivity
            val resultIntent = Intent().apply {
                putExtra(EXTRA_PAIRING_TOKEN, token)
                putExtra(EXTRA_API_URL, apiUrl)
                putExtra(EXTRA_SUCCESS, true)
            }
            setResult(RESULT_OK, resultIntent)

            // Small delay to show the result before closing
            previewView.postDelayed({
                finish()
            }, 500)

        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse QR data: ${e.message}")
            runOnUiThread {
                instructionText.text = "Invalid QR format. Please scan a valid pairing QR."
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
        barcodeScanner.close()
    }

    /**
     * Image analyzer for ML Kit QR detection
     */
    private inner class QrAnalyzer(
        private val onQrFound: (Barcode) -> Unit
    ) : ImageAnalysis.Analyzer {

        @androidx.camera.core.ExperimentalGetImage
        override fun analyze(imageProxy: ImageProxy) {
            val mediaImage = imageProxy.image
            if (mediaImage != null && isScanning) {
                val image = InputImage.fromMediaImage(
                    mediaImage,
                    imageProxy.imageInfo.rotationDegrees
                )

                barcodeScanner.process(image)
                    .addOnSuccessListener { barcodes ->
                        // Find QR codes
                        for (barcode in barcodes) {
                            if (barcode.format == Barcode.FORMAT_QR_CODE) {
                                barcode.rawValue?.let {
                                    Log.d(TAG, "Found QR: $it")
                                    onQrFound(barcode)
                                    return@addOnSuccessListener
                                }
                            }
                        }
                    }
                    .addOnFailureListener { e ->
                        Log.e(TAG, "QR scanning failed: ${e.message}")
                    }
                    .addOnCompleteListener {
                        imageProxy.close()
                    }
            } else {
                imageProxy.close()
            }
        }
    }
}
