package com.mdxvision.service;

import com.mdxvision.dto.TranscriptionDTO;
import com.mdxvision.entity.Session;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
@Slf4j
public class WebSocketService {

    private final SimpMessagingTemplate messagingTemplate;

    /**
     * Send real-time transcription update to session subscribers
     */
    public void sendTranscriptionUpdate(TranscriptionDTO.RealTimeUpdate update) {
        String destination = "/topic/session/" + update.getSessionId() + "/transcription";
        messagingTemplate.convertAndSend(destination, update);
        log.debug("Sent transcription update to session: {}", update.getSessionId());
    }

    /**
     * Send AI-generated note suggestion
     */
    public void sendNoteSuggestion(String sessionId, Object suggestion) {
        String destination = "/topic/session/" + sessionId + "/suggestions";
        messagingTemplate.convertAndSend(destination, suggestion);
    }

    /**
     * Send drug interaction alert
     */
    public void sendDrugAlert(String sessionId, Object alert) {
        String destination = "/topic/session/" + sessionId + "/alerts";
        messagingTemplate.convertAndSend(destination, alert);
    }

    /**
     * Notify session ended
     */
    public void notifySessionEnded(Session session) {
        String destination = "/topic/session/" + session.getId() + "/status";
        messagingTemplate.convertAndSend(destination, 
            java.util.Map.of("status", "COMPLETED", "endTime", session.getEndTime()));
    }

    /**
     * Send to specific user
     */
    public void sendToUser(String userId, String destination, Object payload) {
        messagingTemplate.convertAndSendToUser(userId, destination, payload);
    }
}
