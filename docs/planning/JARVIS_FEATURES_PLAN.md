# MDx Vision - Jarvis-Like AI Features Plan

**Goal:** Transform MDx Vision from a voice-command tool into a proactive AI clinical assistant that anticipates needs, suggests actions, and engages in natural conversation - like Jarvis for healthcare.

**Foundation Already Built:**
- Feature #62: Ambient Clinical Intelligence (passive listening)
- Feature #78: AI Clinical Co-pilot (conversational AI)
- Feature #69: AI Differential Diagnosis
- Voice Intent Chaining (multi-command parsing)
- 100+ voice commands
- RAG knowledge system
- Proactive safety alerts (allergies, labs, vitals, drug interactions)

---

## Phase 1: Proactive Intelligence

### 1.1 Anticipatory Alerts
- [ ] **Pre-Visit Prep Alert** - When loading patient, AI summarizes: "Heads up: A1c due, last BP elevated, mammogram overdue"
- [ ] **Care Gap Detection** - Proactively identify missing screenings/labs based on age, conditions, last dates
- [ ] **Medication Refill Alerts** - "Patient may need refills - last fill was 28 days ago"
- [ ] **Follow-up Reminders** - "This patient was seen 2 weeks ago for chest pain - consider asking about resolution"
- [ ] **Lab Result Context** - When showing labs, auto-compare to previous: "Creatinine up 0.3 from last month"

### 1.2 Smart Notifications During Encounter
- [ ] **Time-Based Prompts** - After 10 min: "You've been with this patient 10 minutes. Typical visit is 15 min."
- [ ] **Documentation Prompts** - After exam discussion detected: "I heard physical exam findings - want me to add them to the note?"
- [ ] **Missed Item Detection** - At end of encounter: "You discussed hypertension but no BP med change was ordered"
- [ ] **Billing Optimization** - "Based on complexity, this qualifies for 99214. Consider adding smoking cessation counseling for 99406."

---

## Phase 2: Contextual Suggestions

### 2.1 Context-Aware Recommendations
- [ ] **Chief Complaint Workflows** - When "chest pain" detected, auto-suggest: "Want me to load the chest pain workup?"
- [ ] **Condition-Based Protocols** - For diabetic: "A1c is 8.2. ADA guidelines suggest medication adjustment. Want me to pull the ADA protocol?"
- [ ] **Drug-Condition Matching** - When prescribing: "Patient has CKD - consider dose adjustment for this medication"
- [ ] **Test Result Actions** - "Troponin is elevated. Want me to order a cardiology consult and repeat troponin?"

### 2.2 Ambient Trigger Suggestions
- [ ] **Symptom Detection → DDx** - When hearing "shortness of breath", offer: "Want me to generate a differential?"
- [ ] **Medication Mention → Interaction Check** - "You mentioned starting metoprolol. Checking interactions... all clear."
- [ ] **Allergy Mention → Update Chart** - "Patient mentioned new penicillin allergy. Want me to add it to their chart?"
- [ ] **Social History Detection** - "I heard patient mention smoking. Want me to update social history and add cessation counseling?"

---

## Phase 3: Natural Conversation AI

### 3.1 Enhanced Co-pilot Dialogue
- [ ] **Multi-Turn Clinical Reasoning** - "What do you think about this rash?" → AI responds → "What if they also have fever?" → AI updates thinking
- [ ] **Clarifying Questions** - AI asks back: "The rash - is it maculopapular or vesicular? That changes my differential."
- [ ] **Teaching Mode** - "Explain why you suggested that diagnosis" → AI provides clinical reasoning with citations
- [ ] **Second Opinion Mode** - "I'm thinking pneumonia. What else should I consider?" → AI challenges with alternatives

### 3.2 Natural Language Understanding
- [ ] **Indirect Commands** - "I need to check on that potassium" → AI interprets as "show labs"
- [ ] **Contextual Pronouns** - "What's his creatinine?" (knows current patient)
- [ ] **Conversational Follow-ups** - "Show labs" → "What about the troponin specifically?" → shows troponin trend
- [ ] **Negation Handling** - "Don't order the CT yet" → cancels pending order

### 3.3 Personality & Rapport
- [ ] **Customizable AI Persona** - Formal vs. casual communication style
- [ ] **Encouragement Mode** - "Good catch on that murmur" after noting physical exam finding
- [ ] **Workload Awareness** - "You've seen 15 patients today. Two more scheduled."
- [ ] **End-of-Day Summary** - "Today you saw 18 patients, completed 15 notes, 3 pending sign-off"

---

## Phase 4: Pattern Recognition

### 4.1 Population Health Insights
- [ ] **Outbreak Detection** - "I've noticed 5 patients today with similar GI symptoms. Possible outbreak?"
- [ ] **Trending Diagnoses** - "URI visits up 40% this week compared to last month"
- [ ] **Panel Analytics** - "12 of your diabetic patients have A1c > 9. Want to see the list?"
- [ ] **Quality Metrics** - "Your door-to-doc time averaged 18 minutes today"

### 4.2 Individual Patient Patterns
- [ ] **Frequent Flyer Detection** - "This patient has visited 4 times in 2 weeks with similar complaints"
- [ ] **Medication Non-Adherence Signals** - "Patient's BP consistently elevated despite 3 medication changes - possible adherence issue"
- [ ] **Deterioration Patterns** - "Weight up 8 lbs over 3 visits. Consider CHF exacerbation."
- [ ] **Appointment Pattern Analysis** - "Patient frequently no-shows. Consider outreach."

---

## Phase 5: Predictive Workflows

### 5.1 Pre-Load Intelligence
- [ ] **Smart Patient Prep** - Before entering room, AI pre-loads likely needed info based on chief complaint
- [ ] **Order Prediction** - For "chest pain", pre-stage EKG, troponin, chest X-ray orders (not submitted, just ready)
- [ ] **Template Suggestion** - Auto-suggest appropriate note template based on visit type
- [ ] **Resource Estimation** - "This visit type typically runs 25 minutes and may need echo"

### 5.2 Workflow Automation
- [ ] **Auto-Documentation** - After ambient mode, AI drafts complete note without explicit command
- [ ] **Smart Routing** - "Based on symptoms, this patient should probably go to radiology first"
- [ ] **Follow-up Scheduling** - "Shall I schedule a 2-week follow-up for BP recheck?"
- [ ] **Referral Auto-Draft** - When referral discussed, AI drafts referral with relevant history

---

## Phase 6: Ambient Intelligence

### 6.1 Always-Aware Mode
- [ ] **Passive Context Building** - AI continuously builds understanding without explicit commands
- [ ] **Room Entry Detection** - Auto-load patient when entering room (via beacon/NFC/proximity)
- [ ] **Conversation State Tracking** - Knows what's been discussed vs. what's pending
- [ ] **Silence Detection** - If no speech for 30 sec during exam, AI stays quiet

### 6.2 Proactive Information Surfacing
- [ ] **Just-In-Time Info** - When hearing "diabetes", patient's A1c appears in HUD without asking
- [ ] **Relevant History Bubble** - During discussion, relevant past visits/notes surface automatically
- [ ] **Drug Info on Mention** - When discussing a medication, dosing/interactions appear
- [ ] **Guideline Pop-ups** - When clinical decision point detected, relevant guideline appears

### 6.3 Smart Interruptions
- [ ] **Urgency-Based Interruption** - Critical lab → immediate spoken alert. Non-critical → visual only.
- [ ] **Conversation Gap Detection** - Only speaks during natural pauses, not over patient
- [ ] **Priority Queue** - Multiple items to surface? Prioritize by clinical importance
- [ ] **Dismissal Memory** - "Not now" for an alert → don't repeat for this patient visit

---

## Implementation Priority

### Wave 1: Quick Wins (Extend Existing Features)
- [ ] Pre-Visit Prep Alert (extend patient load)
- [ ] Lab Result Context (extend lab display)
- [ ] Chief Complaint Workflows (extend ambient mode)
- [ ] Multi-Turn Clinical Reasoning (extend co-pilot)
- [ ] Indirect Commands (extend voice parser)

### Wave 2: High Impact
- [ ] Care Gap Detection
- [ ] Missed Item Detection
- [ ] Symptom Detection → DDx
- [ ] Auto-Documentation after ambient
- [ ] Just-In-Time Info surfacing

### Wave 3: Advanced
- [ ] Outbreak Detection
- [ ] Smart Patient Prep / Order Prediction
- [ ] Room Entry Detection
- [ ] Conversation Gap Detection
- [ ] End-of-Day Summary

---

## Technical Requirements

### Backend Enhancements
- [ ] Patient history aggregation service (for patterns)
- [ ] Clinical rules engine (for care gaps, guidelines)
- [ ] Context state machine (track conversation state)
- [ ] Priority queue for alerts/suggestions
- [ ] Analytics pipeline for population health

### AI/ML Components
- [ ] Intent classification model (for indirect commands)
- [ ] Conversation state tracker
- [ ] Clinical entity linking (symptoms → conditions → orders)
- [ ] Time-series analysis (for trends/patterns)
- [ ] Interruption timing model (conversation gap detection)

### Mobile/HUD Changes
- [ ] Passive notification queue (visual, non-blocking)
- [ ] Priority-based alert rendering
- [ ] Context sidebar/overlay
- [ ] Ambient state machine enhancements
- [ ] Proactive TTS with conversation awareness

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Clinician time saved per patient | 5+ minutes |
| Care gaps identified per day | 10+ per provider |
| User engagement with suggestions | >60% acceptance |
| Alert fatigue (dismissed without action) | <20% |
| Documentation completion same-day | >95% |
| Clinician satisfaction score | >4.5/5 |

---

## Notes

- **Safety First**: All proactive suggestions are just that - suggestions. Clinician always has final say.
- **Alert Fatigue Prevention**: Smart throttling, priority queuing, "don't remind me" options
- **HIPAA Compliance**: All pattern recognition done on de-identified aggregates where possible
- **Personalization**: Learn individual clinician preferences over time (what they accept/dismiss)

---

*Created: January 2026*
*Status: Planning Phase*
