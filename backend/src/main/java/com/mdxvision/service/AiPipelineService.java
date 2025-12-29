package com.mdxvision.service;

import com.mdxvision.entity.Session;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class AiPipelineService {

    private final WebClient.Builder webClientBuilder;

    @Value("${mdx.ai-service.url}")
    private String aiServiceUrl;

    /**
     * Initialize transcription session with AI service
     */
    public void initializeTranscription(Session session) {
        WebClient client = webClientBuilder.baseUrl(aiServiceUrl).build();
        
        Map<String, Object> request = Map.of(
            "sessionId", session.getId().toString(),
            "audioChannelId", session.getAudioChannelId(),
            "languageCode", session.getLanguageCode(),
            "translationTarget", session.getTranslationTargetLanguage() != null 
                ? session.getTranslationTargetLanguage() : "",
            "encounterId", session.getEncounter() != null 
                ? session.getEncounter().getId().toString() : ""
        );

        client.post()
            .uri("/v1/transcription/start")
            .contentType(MediaType.APPLICATION_JSON)
            .bodyValue(request)
            .retrieve()
            .bodyToMono(Void.class)
            .doOnSuccess(v -> log.info("Transcription initialized for session: {}", session.getId()))
            .doOnError(e -> log.error("Failed to initialize transcription: {}", e.getMessage()))
            .subscribe();
    }

    /**
     * Stop transcription session
     */
    public void stopTranscription(Session session) {
        WebClient client = webClientBuilder.baseUrl(aiServiceUrl).build();

        client.post()
            .uri("/v1/transcription/stop/" + session.getId())
            .retrieve()
            .bodyToMono(Void.class)
            .doOnSuccess(v -> log.info("Transcription stopped for session: {}", session.getId()))
            .doOnError(e -> log.error("Failed to stop transcription: {}", e.getMessage()))
            .subscribe();
    }

    /**
     * Generate clinical note from transcriptions
     */
    public Mono<Map<String, Object>> generateClinicalNote(String encounterId, String noteType) {
        WebClient client = webClientBuilder.baseUrl(aiServiceUrl).build();

        Map<String, Object> request = Map.of(
            "encounterId", encounterId,
            "noteType", noteType
        );

        return client.post()
            .uri("/v1/notes/generate")
            .contentType(MediaType.APPLICATION_JSON)
            .bodyValue(request)
            .retrieve()
            .bodyToMono(Map.class)
            .map(response -> (Map<String, Object>) response)
            .doOnSuccess(v -> log.info("Clinical note generated for encounter: {}", encounterId))
            .doOnError(e -> log.error("Failed to generate clinical note: {}", e.getMessage()));
    }

    /**
     * Check for drug interactions
     */
    public Mono<Map<String, Object>> checkDrugInteractions(String medicationText) {
        WebClient client = webClientBuilder.baseUrl(aiServiceUrl).build();

        return client.post()
            .uri("/v1/drugs/check-interactions")
            .contentType(MediaType.APPLICATION_JSON)
            .bodyValue(Map.of("text", medicationText))
            .retrieve()
            .bodyToMono(Map.class)
            .map(response -> (Map<String, Object>) response);
    }

    /**
     * Translate text
     */
    public Mono<String> translate(String text, String sourceLanguage, String targetLanguage) {
        WebClient client = webClientBuilder.baseUrl(aiServiceUrl).build();

        Map<String, Object> request = Map.of(
            "text", text,
            "sourceLanguage", sourceLanguage,
            "targetLanguage", targetLanguage
        );

        return client.post()
            .uri("/v1/translate")
            .contentType(MediaType.APPLICATION_JSON)
            .bodyValue(request)
            .retrieve()
            .bodyToMono(Map.class)
            .map(response -> (String) response.get("translatedText"));
    }
}
