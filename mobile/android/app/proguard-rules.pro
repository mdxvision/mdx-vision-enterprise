# MDx Vision ProGuard Rules

# React Native
-keep class com.facebook.react.** { *; }
-keep class com.facebook.hermes.** { *; }

# Vuzix SDK
-keep class com.vuzix.** { *; }
-keep interface com.vuzix.** { *; }

# ML Kit
-keep class com.google.mlkit.** { *; }

# OkHttp
-keep class okhttp3.** { *; }
-keep interface okhttp3.** { *; }
-dontwarn okhttp3.**

# MDx Vision
-keep class com.mdxvision.** { *; }
