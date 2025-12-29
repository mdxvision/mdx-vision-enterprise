package com.mdxvision.fhir;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import ca.uhn.fhir.context.FhirContext;
import ca.uhn.fhir.rest.client.api.IGenericClient;
import ca.uhn.fhir.rest.client.interceptor.BearerTokenAuthInterceptor;

/**
 * Epic FHIR R4 Configuration
 *
 * Supports:
 * - Epic on FHIR (open.epic.com) sandbox
 * - Production Epic instances
 * - Patient, Observation, Encounter resources
 */
@Configuration
public class EpicFhirConfig {

    @Value("${mdx.epic.base-url:https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4}")
    private String epicBaseUrl;

    @Value("${mdx.epic.access-token:}")
    private String accessToken;

    @Value("${mdx.epic.client-id:}")
    private String clientId;

    @Bean
    public FhirContext fhirContext() {
        return FhirContext.forR4();
    }

    @Bean
    public IGenericClient epicFhirClient(FhirContext fhirContext) {
        IGenericClient client = fhirContext.newRestfulGenericClient(epicBaseUrl);

        // Add auth if token provided
        if (accessToken != null && !accessToken.isEmpty()) {
            client.registerInterceptor(new BearerTokenAuthInterceptor(accessToken));
        }

        return client;
    }
}
