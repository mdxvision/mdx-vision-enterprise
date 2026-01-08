package com.mdxvision

data class PendingClarification(
    val question: String,
    val expectedSlot: String,
)

data class ConversationState(
    var currentPatientId: String? = null,
    var currentPatientName: String? = null,
    var lastViewedSection: String? = null,
    var lastIntent: String? = null,
    var pendingClarification: PendingClarification? = null,
)
