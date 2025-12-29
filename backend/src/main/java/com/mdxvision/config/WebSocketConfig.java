package com.mdxvision.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.web.socket.config.annotation.EnableWebSocketMessageBroker;
import org.springframework.web.socket.config.annotation.StompEndpointRegistry;
import org.springframework.web.socket.config.annotation.WebSocketMessageBrokerConfigurer;

@Configuration
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

    @Override
    public void configureMessageBroker(MessageBrokerRegistry config) {
        // Enable a simple memory-based message broker
        config.enableSimpleBroker(
            "/topic",    // For broadcast messages (transcription updates)
            "/queue"     // For user-specific messages (alerts, notifications)
        );
        config.setApplicationDestinationPrefixes("/app");
        config.setUserDestinationPrefix("/user");
    }

    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        registry.addEndpoint("/ws")
            .setAllowedOrigins(
                "http://localhost:3000",
                "http://localhost:5173",
                "https://*.mdx.vision"
            )
            .withSockJS();
        
        // Native WebSocket endpoint for React Native
        registry.addEndpoint("/ws-native")
            .setAllowedOrigins("*");
    }
}
