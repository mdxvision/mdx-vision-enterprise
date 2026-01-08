    private val conversationState = ConversationState()
    private fun updateConversationPatient(patientId: String, name: String?) {
        conversationState.currentPatientId = patientId
        conversationState.currentPatientName = name
        conversationState.lastViewedSection = null
        conversationState.lastIntent = "loadPatient"
        conversationState.pendingClarification = null
    }

    private fun updateConversationSection(section: String) {
        conversationState.lastViewedSection = section
        conversationState.lastIntent = "showSection"
    }

    private fun setPendingClarification(question: String, expectedSlot: String) {
        conversationState.pendingClarification = PendingClarification(question, expectedSlot)
    }

    private fun clearPendingClarification() {
        conversationState.pendingClarification = null
    }

                updateConversationPatient(patientId, name)
                            updateConversationPatient(patientId, name)
                        updateConversationPatient(patientId, name)
            updateConversationSection(section)
                                updateConversationSection(section)
        conversationState.lastIntent = "searchPatients"
