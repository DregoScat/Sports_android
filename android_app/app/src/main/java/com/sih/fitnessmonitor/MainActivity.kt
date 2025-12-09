package com.sih.fitnessmonitor

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.sih.fitnessmonitor.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityMainBinding
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        setupUI()
    }
    
    private fun setupUI() {
        // Server IP input - default to localhost for emulator
        binding.etServerIp.setText("10.0.2.2") // Android emulator localhost
        binding.etServerPort.setText("5000")
        
        // Squat Mode Button
        binding.btnSquatMode.setOnClickListener {
            startStream("squat")
        }
        
        // Jump Mode Button
        binding.btnJumpMode.setOnClickListener {
            startStream("jump")
        }
        
        // Connect Button
        binding.btnConnect.setOnClickListener {
            testConnection()
        }
    }
    
    private fun getServerUrl(): String {
        val ip = binding.etServerIp.text.toString().trim()
        val port = binding.etServerPort.text.toString().trim()
        return "http://$ip:$port"
    }
    
    private fun startStream(mode: String) {
        val serverUrl = getServerUrl()
        if (serverUrl.isBlank()) {
            Toast.makeText(this, "Please enter server IP", Toast.LENGTH_SHORT).show()
            return
        }
        
        val intent = Intent(this, StreamActivity::class.java).apply {
            putExtra("SERVER_URL", serverUrl)
            putExtra("MODE", mode)
        }
        startActivity(intent)
    }
    
    private fun testConnection() {
        val serverUrl = getServerUrl()
        Toast.makeText(this, "Testing connection to $serverUrl...", Toast.LENGTH_SHORT).show()
        
        Thread {
            try {
                val url = java.net.URL(serverUrl)
                val connection = url.openConnection() as java.net.HttpURLConnection
                connection.connectTimeout = 5000
                connection.readTimeout = 5000
                connection.requestMethod = "GET"
                
                val responseCode = connection.responseCode
                runOnUiThread {
                    if (responseCode == 200) {
                        Toast.makeText(this, "Connected successfully!", Toast.LENGTH_SHORT).show()
                        binding.tvStatus.text = "Status: Connected ✓"
                        binding.tvStatus.setTextColor(getColor(R.color.green))
                    } else {
                        Toast.makeText(this, "Server returned: $responseCode", Toast.LENGTH_SHORT).show()
                        binding.tvStatus.text = "Status: Error ($responseCode)"
                        binding.tvStatus.setTextColor(getColor(R.color.red))
                    }
                }
                connection.disconnect()
            } catch (e: Exception) {
                runOnUiThread {
                    Toast.makeText(this, "Connection failed: ${e.message}", Toast.LENGTH_LONG).show()
                    binding.tvStatus.text = "Status: Disconnected ✗"
                    binding.tvStatus.setTextColor(getColor(R.color.red))
                }
            }
        }.start()
    }
}
