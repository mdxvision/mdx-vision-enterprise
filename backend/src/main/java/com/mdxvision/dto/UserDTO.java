package com.mdxvision.dto;

import com.mdxvision.entity.User;
import lombok.*;

import java.util.UUID;

public class UserDTO {

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Response {
        private UUID id;
        private String email;
        private String firstName;
        private String lastName;
        private String fullName;
        private User.UserRole role;
        private User.UserVertical vertical;
        private String organizationId;
        private String npiNumber;
        private String specialty;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CreateRequest {
        private String email;
        private String firstName;
        private String lastName;
        private User.UserRole role;
        private User.UserVertical vertical;
        private String organizationId;
        private String npiNumber;
        private String specialty;
    }
}
