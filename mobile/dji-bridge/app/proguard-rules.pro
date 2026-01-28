# DJI SDK ProGuard rules
-keepclassmembers class * extends android.app.Service
-keepclassmembers class * extends android.content.BroadcastReceiver
-keepclassmembers class * extends android.app.Activity

# DJI SDK
-keep class dji.** { *; }
-keep class com.dji.** { *; }
-dontwarn dji.**
-dontwarn com.dji.**

# NanoHTTPD
-keep class fi.iki.elonen.** { *; }

# Gson
-keepattributes Signature
-keepattributes *Annotation*
-keep class com.google.gson.** { *; }
-keep class * implements com.google.gson.TypeAdapterFactory
-keep class * implements com.google.gson.JsonSerializer
-keep class * implements com.google.gson.JsonDeserializer
