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
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * MDx Vision - Barcode Scanner Activity
 * Patent Implementation: Claims 5-7 (Camera patient identification)
 *
 * Scans patient wristband barcodes to lookup patient by MRN
 */
class BarcodeScannerActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "MDxBarcode"
        private const val CAMERA_PERMISSION_CODE = 1002
        const val EXTRA_MRN = "scanned_mrn"
        const val EXTRA_PATIENT_ID = "patient_id"
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
            text = "Scan Patient Wristband"
            textSize = 24f
            setTextColor(0xFFFFFFFF.toInt())
        }
        overlayLayout.addView(statusText)

        instructionText = TextView(this).apply {
            text = "Point camera at barcode on patient wristband"
            textSize = 16f
            setTextColor(0xFFCCCCCC.toInt())
            setPadding(0, 8, 0, 0)
        }
        overlayLayout.addView(instructionText)

        layout.addView(overlayLayout)

        // Scan frame overlay (visual guide)
        val scanFrame = android.view.View(this).apply {
            layoutParams = android.widget.FrameLayout.LayoutParams(600, 300).apply {
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
                Toast.makeText(this, "Camera permission required", Toast.LENGTH_SHORT).show()
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

            // Image analysis for barcode scanning
            val imageAnalyzer = ImageAnalysis.Builder()
                .setTargetResolution(Size(1280, 720))
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
                .also {
                    it.setAnalyzer(cameraExecutor, BarcodeAnalyzer { barcode ->
                        onBarcodeDetected(barcode)
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

    private fun onBarcodeDetected(barcode: Barcode) {
        if (!isScanning) return
        isScanning = false

        val rawValue = barcode.rawValue ?: return
        Log.d(TAG, "Barcode detected: $rawValue (format: ${barcode.format})")

        runOnUiThread {
            statusText.text = "Barcode Found!"
            instructionText.text = "MRN: $rawValue"
        }

        // Return result to MainActivity
        val resultIntent = Intent().apply {
            putExtra(EXTRA_MRN, rawValue)
        }
        setResult(RESULT_OK, resultIntent)

        // Small delay to show the result before closing
        previewView.postDelayed({
            finish()
        }, 500)
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
        barcodeScanner.close()
    }

    /**
     * Image analyzer for ML Kit barcode detection
     */
    private inner class BarcodeAnalyzer(
        private val onBarcodeFound: (Barcode) -> Unit
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
                        // Find the first valid barcode
                        for (barcode in barcodes) {
                            barcode.rawValue?.let {
                                Log.d(TAG, "Found barcode: $it")
                                onBarcodeFound(barcode)
                                return@addOnSuccessListener
                            }
                        }
                    }
                    .addOnFailureListener { e ->
                        Log.e(TAG, "Barcode scanning failed: ${e.message}")
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
