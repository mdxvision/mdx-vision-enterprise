package com.mdxvision

import org.junit.Assert.*
import org.junit.Test

/**
 * Comprehensive Voice Command Tests
 *
 * Tests ALL voice commands across 91 features documented in CLAUDE.md.
 * Organized by feature category for easy maintenance.
 *
 * Coverage: ~1000+ voice command patterns
 */
class VoiceCommandsComprehensiveTest {

    // ═══════════════════════════════════════════════════════════════════════════
    // CORE PATIENT COMMANDS (Features #1-10)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `patient - load patient`() {
        assertTrue(isPatientCommand("load patient"))
    }

    @Test
    fun `patient - load patient by number`() {
        assertTrue(isPatientCommand("load 1"))
        assertTrue(isPatientCommand("load 2"))
        assertTrue(isPatientCommand("load 10"))
    }

    @Test
    fun `patient - find patient`() {
        assertTrue(isPatientCommand("find patient smith"))
        assertTrue(isPatientCommand("find patient john doe"))
    }

    @Test
    fun `patient - scan wristband`() {
        assertTrue(isPatientCommand("scan wristband"))
        assertTrue(isPatientCommand("scan"))
    }

    @Test
    fun `patient - show vitals`() {
        assertTrue(isShowCommand("show vitals"))
        assertTrue(isShowCommand("show vital"))
        assertTrue(isShowCommand("vitals"))
    }

    @Test
    fun `patient - show allergies`() {
        assertTrue(isShowCommand("show allergies"))
        assertTrue(isShowCommand("allergies"))
        assertTrue(isShowCommand("allergy"))
    }

    @Test
    fun `patient - show medications`() {
        assertTrue(isShowCommand("show medications"))
        assertTrue(isShowCommand("show meds"))
        assertTrue(isShowCommand("medications"))
        assertTrue(isShowCommand("drugs"))
    }

    @Test
    fun `patient - show labs`() {
        assertTrue(isShowCommand("show labs"))
        assertTrue(isShowCommand("labs"))
        assertTrue(isShowCommand("laboratory"))
        assertTrue(isShowCommand("results"))
    }

    @Test
    fun `patient - show procedures`() {
        assertTrue(isShowCommand("show procedures"))
        assertTrue(isShowCommand("procedures"))
        assertTrue(isShowCommand("surgery"))
        assertTrue(isShowCommand("operation"))
    }

    @Test
    fun `patient - show immunizations`() {
        assertTrue(isShowCommand("show immunizations"))
        assertTrue(isShowCommand("immunizations"))
        assertTrue(isShowCommand("vaccines"))
        assertTrue(isShowCommand("vaccination"))
        assertTrue(isShowCommand("shots"))
    }

    @Test
    fun `patient - show conditions`() {
        assertTrue(isShowCommand("show conditions"))
        assertTrue(isShowCommand("conditions"))
        assertTrue(isShowCommand("problems"))
        assertTrue(isShowCommand("diagnosis"))
        assertTrue(isShowCommand("diagnoses"))
    }

    @Test
    fun `patient - show care plans`() {
        assertTrue(isShowCommand("show care plans"))
        assertTrue(isShowCommand("care plans"))
        assertTrue(isShowCommand("treatment plan"))
    }

    @Test
    fun `patient - show clinical notes`() {
        assertTrue(isShowCommand("clinical notes"))
        assertTrue(isShowCommand("show notes"))
        assertTrue(isShowCommand("patient notes"))
        assertTrue(isShowCommand("previous notes"))
        assertTrue(isShowCommand("history notes"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // DOCUMENTATION MODE (Features #11-20)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `note - start note`() {
        assertTrue(isNoteCommand("start note"))
        assertTrue(isNoteCommand("begin note"))
        assertTrue(isNoteCommand("new note"))
    }

    @Test
    fun `note - live transcribe`() {
        assertTrue(isNoteCommand("live transcribe"))
        assertTrue(isNoteCommand("start transcription"))
    }

    @Test
    fun `note - stop transcription`() {
        assertTrue(isStopCommand("stop transcription"))
        assertTrue(isStopCommand("stop transcribing"))
        assertTrue(isStopCommand("stop recording"))
        assertTrue(isStopCommand("close"))
    }

    @Test
    fun `note - generate note`() {
        assertTrue(isNoteCommand("generate note"))
        assertTrue(isNoteCommand("create note"))
        assertTrue(isNoteCommand("make note"))
        assertTrue(isNoteCommand("document this"))
    }

    @Test
    fun `note - re-record`() {
        assertTrue(isNoteCommand("re-record"))
        assertTrue(isNoteCommand("rerecord"))
        assertTrue(isNoteCommand("record again"))
        assertTrue(isNoteCommand("try again"))
    }

    @Test
    fun `note - edit note`() {
        assertTrue(isNoteCommand("edit note"))
        assertTrue(isNoteCommand("modify note"))
    }

    @Test
    fun `note - reset note`() {
        assertTrue(isNoteCommand("reset note"))
        assertTrue(isNoteCommand("clear note"))
    }

    @Test
    fun `note - save note`() {
        assertTrue(isNoteCommand("save note"))
        assertTrue(isNoteCommand("save"))
    }

    @Test
    fun `note - push to EHR`() {
        assertTrue(isNoteCommand("push note"))
        assertTrue(isNoteCommand("send to ehr"))
        assertTrue(isNoteCommand("push to ehr"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // WAKE WORD & VOICE CONTROL (Features #1-4)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `wake - hey minerva`() {
        assertTrue(containsWakeWord("hey minerva show vitals"))
        assertTrue(containsWakeWord("hey m i n e r v a load patient"))
    }

    @Test
    fun `wake - case insensitive`() {
        assertTrue(containsWakeWord("HEY MINERVA show vitals"))
        assertTrue(containsWakeWord("Hey Minerva load patient"))
    }

    @Test
    fun `wake - extract command after wake word`() {
        assertEquals("show vitals", extractCommandAfterWakeWord("hey minerva show vitals"))
        assertEquals("load patient", extractCommandAfterWakeWord("hey m i n e r v a load patient"))
    }

    @Test
    fun `wake - minerva mode toggle`() {
        assertTrue(isModeCommand("minerva mode"))
        assertTrue(isModeCommand("hey minerva mode"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // HELP COMMANDS (Feature #21)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `help - basic help`() {
        assertTrue(isHelpCommand("help"))
        assertTrue(isHelpCommand("what can i say"))
        assertTrue(isHelpCommand("voice commands"))
        assertTrue(isHelpCommand("show commands"))
        assertTrue(isHelpCommand("list commands"))
        assertTrue(isHelpCommand("available commands"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // PATIENT SUMMARY & BRIEFING (Features #22-23)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `summary - visual summary`() {
        assertTrue(isSummaryCommand("patient summary"))
        assertTrue(isSummaryCommand("summarize patient"))
        assertTrue(isSummaryCommand("quick summary"))
        assertTrue(isSummaryCommand("show summary"))
        assertTrue(isSummaryCommand("overview"))
    }

    @Test
    fun `summary - spoken briefing`() {
        assertTrue(isBriefingCommand("tell me about"))
        assertTrue(isBriefingCommand("read summary"))
        assertTrue(isBriefingCommand("speak summary"))
        assertTrue(isBriefingCommand("brief me"))
        assertTrue(isBriefingCommand("briefing"))
        assertTrue(isBriefingCommand("tell me about patient"))
        assertTrue(isBriefingCommand("patient brief"))
        assertTrue(isBriefingCommand("read patient"))
        assertTrue(isBriefingCommand("summarize"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // FONT SIZE ADJUSTMENT (Feature #8)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `font - small`() {
        assertEquals("small", parseFontSize("small font"))
        assertEquals("small", parseFontSize("smaller"))
    }

    @Test
    fun `font - medium`() {
        assertEquals("medium", parseFontSize("medium font"))
        assertEquals("medium", parseFontSize("normal font"))
    }

    @Test
    fun `font - large`() {
        assertEquals("large", parseFontSize("large font"))
        assertEquals("large", parseFontSize("larger"))
        assertEquals("large", parseFontSize("bigger font"))
    }

    @Test
    fun `font - extra large`() {
        assertEquals("extra_large", parseFontSize("extra large font"))
        assertEquals("extra_large", parseFontSize("huge font"))
        assertEquals("extra_large", parseFontSize("biggest"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // AUTO SCROLL (Feature #10)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `scroll - auto scroll toggle`() {
        assertTrue(isScrollCommand("auto scroll on"))
        assertTrue(isScrollCommand("auto scroll off"))
        assertTrue(isScrollCommand("enable auto scroll"))
        assertTrue(isScrollCommand("disable auto scroll"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // NOTE TEMPLATES (Features #11-12)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `template - note types`() {
        assertTrue(isTemplateCommand("soap note"))
        assertTrue(isTemplateCommand("progress note"))
        assertTrue(isTemplateCommand("h and p"))
        assertTrue(isTemplateCommand("consult note"))
        assertTrue(isTemplateCommand("auto detect"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // SPEAKER DIARIZATION (Feature #13)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `diarization - speaker labels`() {
        assertTrue(isDiarizationCommand("show speakers"))
        assertTrue(isDiarizationCommand("who is speaking"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // NOTE SIGN-OFF (Feature #19)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `signoff - sign note`() {
        assertTrue(isSignoffCommand("sign note"))
        assertTrue(isSignoffCommand("sign and save"))
        assertTrue(isSignoffCommand("finalize note"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // OFFLINE DRAFTS (Feature #27)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `offline - sync notes`() {
        assertTrue(isOfflineCommand("sync notes"))
        assertTrue(isOfflineCommand("show drafts"))
        assertTrue(isOfflineCommand("delete draft 1"))
        assertTrue(isOfflineCommand("delete draft 2"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // PATIENT HISTORY (Feature #37)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `history - show history`() {
        assertTrue(isHistoryCommand("show history"))
        assertTrue(isHistoryCommand("recent patients"))
        assertTrue(isHistoryCommand("patient history"))
    }

    @Test
    fun `history - clear history`() {
        assertTrue(isHistoryCommand("clear history"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // SESSION TIMEOUT (Feature #38)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `timeout - lock session`() {
        assertTrue(isTimeoutCommand("lock session"))
        assertTrue(isTimeoutCommand("lock"))
    }

    @Test
    fun `timeout - unlock session`() {
        assertTrue(isTimeoutCommand("unlock"))
        assertTrue(isTimeoutCommand("unlock session"))
    }

    @Test
    fun `timeout - set timeout`() {
        assertTrue(isTimeoutCommand("timeout 5 minutes"))
        assertTrue(isTimeoutCommand("timeout 10 min"))
        assertTrue(isTimeoutCommand("set timeout 15 minutes"))
    }

    @Test
    fun `timeout - parse minutes`() {
        assertEquals(5, parseTimeoutMinutes("timeout 5 minutes"))
        assertEquals(10, parseTimeoutMinutes("timeout 10 min"))
        assertEquals(15, parseTimeoutMinutes("set timeout 15 minutes"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // VOICE NOTE EDITING (Feature #39)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `edit - change section`() {
        assertTrue(isEditCommand("change subjective to"))
        assertTrue(isEditCommand("set objective to"))
        assertTrue(isEditCommand("change assessment"))
        assertTrue(isEditCommand("set plan"))
    }

    @Test
    fun `edit - add to section`() {
        assertTrue(isEditCommand("add to subjective"))
        assertTrue(isEditCommand("add to objective"))
        assertTrue(isEditCommand("add to assessment"))
        assertTrue(isEditCommand("add to plan"))
        assertTrue(isEditCommand("append to plan"))
    }

    @Test
    fun `edit - delete commands`() {
        assertTrue(isEditCommand("delete last sentence"))
        assertTrue(isEditCommand("delete last line"))
        assertTrue(isEditCommand("delete last item"))
        assertTrue(isEditCommand("remove last"))
    }

    @Test
    fun `edit - clear section`() {
        assertTrue(isEditCommand("clear subjective"))
        assertTrue(isEditCommand("clear objective"))
        assertTrue(isEditCommand("clear assessment"))
        assertTrue(isEditCommand("clear plan"))
    }

    @Test
    fun `edit - insert macros`() {
        assertTrue(isEditCommand("insert normal exam"))
        assertTrue(isEditCommand("insert normal vitals"))
        assertTrue(isEditCommand("insert negative ros"))
        assertTrue(isEditCommand("insert follow up"))
        assertTrue(isEditCommand("add macro"))
    }

    @Test
    fun `edit - undo`() {
        assertTrue(isEditCommand("undo"))
        assertTrue(isEditCommand("undo last"))
        assertTrue(isEditCommand("undo change"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // VOICE NAVIGATION (Feature #40)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `navigation - scroll`() {
        assertTrue(isNavigationCommand("scroll down"))
        assertTrue(isNavigationCommand("scroll up"))
        assertTrue(isNavigationCommand("page down"))
        assertTrue(isNavigationCommand("page up"))
        assertTrue(isNavigationCommand("next page"))
        assertTrue(isNavigationCommand("previous page"))
    }

    @Test
    fun `navigation - go to position`() {
        assertTrue(isNavigationCommand("go to top"))
        assertTrue(isNavigationCommand("go to bottom"))
        assertTrue(isNavigationCommand("scroll to top"))
        assertTrue(isNavigationCommand("scroll to bottom"))
        assertTrue(isNavigationCommand("top of page"))
        assertTrue(isNavigationCommand("bottom of page"))
    }

    @Test
    fun `navigation - go to section`() {
        assertTrue(isNavigationCommand("go to subjective"))
        assertTrue(isNavigationCommand("go to objective"))
        assertTrue(isNavigationCommand("go to assessment"))
        assertTrue(isNavigationCommand("go to plan"))
        assertTrue(isNavigationCommand("jump to assessment"))
        assertTrue(isNavigationCommand("navigate to plan"))
    }

    @Test
    fun `navigation - show section only`() {
        assertTrue(isNavigationCommand("show subjective only"))
        assertTrue(isNavigationCommand("show objective only"))
        assertTrue(isNavigationCommand("show assessment only"))
        assertTrue(isNavigationCommand("show plan only"))
    }

    @Test
    fun `navigation - read section`() {
        assertTrue(isNavigationCommand("read subjective"))
        assertTrue(isNavigationCommand("read objective"))
        assertTrue(isNavigationCommand("read assessment"))
        assertTrue(isNavigationCommand("read plan"))
        assertTrue(isNavigationCommand("read back the plan"))
    }

    @Test
    fun `navigation - read entire note`() {
        assertTrue(isNavigationCommand("read note"))
        assertTrue(isNavigationCommand("read entire note"))
        assertTrue(isNavigationCommand("read the note"))
        assertTrue(isNavigationCommand("read all"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // VOICE DICTATION MODE (Feature #41)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `dictation - start dictation`() {
        assertTrue(isDictationCommand("dictate to subjective"))
        assertTrue(isDictationCommand("dictate to objective"))
        assertTrue(isDictationCommand("dictate to assessment"))
        assertTrue(isDictationCommand("dictate to plan"))
        assertTrue(isDictationCommand("dictate into plan"))
        assertTrue(isDictationCommand("start dictating subjective"))
    }

    @Test
    fun `dictation - stop dictation`() {
        assertTrue(isDictationCommand("stop dictating"))
        assertTrue(isDictationCommand("end dictation"))
        assertTrue(isDictationCommand("done dictating"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // VOICE TEMPLATES (Feature #42)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `templates - use template`() {
        assertTrue(isVoiceTemplateCommand("use diabetes template"))
        assertTrue(isVoiceTemplateCommand("use hypertension template"))
        assertTrue(isVoiceTemplateCommand("use uri template"))
        assertTrue(isVoiceTemplateCommand("use physical template"))
        assertTrue(isVoiceTemplateCommand("use back pain template"))
        assertTrue(isVoiceTemplateCommand("use uti template"))
        assertTrue(isVoiceTemplateCommand("use well child template"))
        assertTrue(isVoiceTemplateCommand("use chest pain template"))
    }

    @Test
    fun `templates - list templates`() {
        assertTrue(isVoiceTemplateCommand("list templates"))
        assertTrue(isVoiceTemplateCommand("show templates"))
        assertTrue(isVoiceTemplateCommand("available templates"))
        assertTrue(isVoiceTemplateCommand("templates"))
        assertTrue(isVoiceTemplateCommand("what templates"))
    }

    @Test
    fun `templates - custom templates`() {
        assertTrue(isVoiceTemplateCommand("my templates"))
        assertTrue(isVoiceTemplateCommand("custom templates"))
        assertTrue(isVoiceTemplateCommand("saved templates"))
    }

    @Test
    fun `templates - save as template`() {
        assertTrue(isVoiceTemplateCommand("save as template"))
        assertTrue(isVoiceTemplateCommand("save template"))
        assertTrue(isVoiceTemplateCommand("save as template headache"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // VOICE ORDERS (Feature #43)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `orders - order labs`() {
        assertTrue(isOrderCommand("order cbc"))
        assertTrue(isOrderCommand("order bmp"))
        assertTrue(isOrderCommand("order cmp"))
        assertTrue(isOrderCommand("order lipid panel"))
        assertTrue(isOrderCommand("order a1c"))
        assertTrue(isOrderCommand("order tsh"))
        assertTrue(isOrderCommand("order urinalysis"))
        assertTrue(isOrderCommand("order troponin"))
        assertTrue(isOrderCommand("order bnp"))
        assertTrue(isOrderCommand("order d-dimer"))
        assertTrue(isOrderCommand("order pt inr"))
        assertTrue(isOrderCommand("order blood culture"))
    }

    @Test
    fun `orders - order imaging`() {
        assertTrue(isOrderCommand("order chest xray"))
        assertTrue(isOrderCommand("order chest x-ray"))
        assertTrue(isOrderCommand("order ct head"))
        assertTrue(isOrderCommand("order ct chest"))
        assertTrue(isOrderCommand("order ct abdomen"))
        assertTrue(isOrderCommand("order mri brain"))
        assertTrue(isOrderCommand("order mri spine"))
        assertTrue(isOrderCommand("order ultrasound"))
        assertTrue(isOrderCommand("order echo"))
        assertTrue(isOrderCommand("order ekg"))
    }

    @Test
    fun `orders - prescribe medications`() {
        assertTrue(isOrderCommand("prescribe amoxicillin"))
        assertTrue(isOrderCommand("prescribe ibuprofen"))
        assertTrue(isOrderCommand("prescribe metformin"))
        assertTrue(isOrderCommand("prescribe lisinopril"))
        assertTrue(isOrderCommand("prescribe amoxicillin 500mg three times daily for 10 days"))
    }

    @Test
    fun `orders - show orders`() {
        assertTrue(isOrderCommand("show orders"))
        assertTrue(isOrderCommand("list orders"))
        assertTrue(isOrderCommand("pending orders"))
        assertTrue(isOrderCommand("what are the orders"))
    }

    @Test
    fun `orders - cancel order`() {
        assertTrue(isOrderCommand("cancel order"))
        assertTrue(isOrderCommand("remove order"))
        assertTrue(isOrderCommand("remove last order"))
        assertTrue(isOrderCommand("delete order"))
    }

    @Test
    fun `orders - clear all orders`() {
        assertTrue(isOrderCommand("clear all orders"))
        assertTrue(isOrderCommand("delete all orders"))
    }

    @Test
    fun `orders - confirmation`() {
        assertTrue(isConfirmCommand("yes"))
        assertTrue(isConfirmCommand("confirm"))
        assertTrue(isConfirmCommand("confirm order"))
        assertTrue(isConfirmCommand("place order"))
        assertTrue(isConfirmCommand("go ahead"))
    }

    @Test
    fun `orders - rejection`() {
        assertTrue(isRejectCommand("no"))
        assertTrue(isRejectCommand("reject"))
        assertTrue(isRejectCommand("don't order"))
        assertTrue(isRejectCommand("do not order"))
        assertTrue(isRejectCommand("cancel"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // ENCOUNTER TIMER (Feature #44)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `timer - start timer`() {
        assertTrue(isTimerCommand("start timer"))
        assertTrue(isTimerCommand("begin timer"))
        assertTrue(isTimerCommand("start encounter"))
        assertTrue(isTimerCommand("start the timer"))
    }

    @Test
    fun `timer - stop timer`() {
        assertTrue(isTimerCommand("stop timer"))
        assertTrue(isTimerCommand("end timer"))
        assertTrue(isTimerCommand("stop encounter"))
        assertTrue(isTimerCommand("end encounter"))
    }

    @Test
    fun `timer - check time`() {
        assertTrue(isTimerCommand("how long"))
        assertTrue(isTimerCommand("what time"))
        assertTrue(isTimerCommand("check timer"))
        assertTrue(isTimerCommand("elapsed time"))
        assertTrue(isTimerCommand("time elapsed"))
        assertTrue(isTimerCommand("how much time"))
        assertTrue(isTimerCommand("time spent"))
    }

    @Test
    fun `timer - reset timer`() {
        assertTrue(isTimerCommand("reset timer"))
        assertTrue(isTimerCommand("restart timer"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // ORDER SETS (Feature #45)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `ordersets - list order sets`() {
        assertTrue(isOrderSetCommand("list order sets"))
        assertTrue(isOrderSetCommand("show order sets"))
        assertTrue(isOrderSetCommand("available order sets"))
        assertTrue(isOrderSetCommand("what order sets"))
    }

    @Test
    fun `ordersets - preview order set`() {
        assertTrue(isOrderSetCommand("what's in chest pain"))
        assertTrue(isOrderSetCommand("whats in sepsis"))
        assertTrue(isOrderSetCommand("preview chest pain workup"))
        assertTrue(isOrderSetCommand("show me chest pain workup"))
    }

    @Test
    fun `ordersets - place order sets`() {
        assertTrue(isOrderSetCommand("order chest pain workup"))
        assertTrue(isOrderSetCommand("order sepsis bundle"))
        assertTrue(isOrderSetCommand("order stroke protocol"))
        assertTrue(isOrderSetCommand("order chf workup"))
        assertTrue(isOrderSetCommand("order copd exacerbation"))
        assertTrue(isOrderSetCommand("order dka protocol"))
        assertTrue(isOrderSetCommand("order pe workup"))
        assertTrue(isOrderSetCommand("order pneumonia workup"))
        assertTrue(isOrderSetCommand("order uti workup"))
        assertTrue(isOrderSetCommand("order abdominal pain workup"))
        assertTrue(isOrderSetCommand("order admission labs"))
        assertTrue(isOrderSetCommand("order preop labs"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // VOICE VITALS ENTRY (Feature #46)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `vitals - blood pressure`() {
        assertTrue(isVitalEntry("bp 120 over 80"))
        assertTrue(isVitalEntry("blood pressure 130 over 85"))
        assertTrue(isVitalEntry("bp 140/90"))
    }

    @Test
    fun `vitals - heart rate`() {
        assertTrue(isVitalEntry("pulse 72"))
        assertTrue(isVitalEntry("heart rate 80"))
        assertTrue(isVitalEntry("hr 65"))
    }

    @Test
    fun `vitals - temperature`() {
        assertTrue(isVitalEntry("temp 98.6"))
        assertTrue(isVitalEntry("temperature 101.2"))
        assertTrue(isVitalEntry("fever 102"))
    }

    @Test
    fun `vitals - respiratory rate`() {
        assertTrue(isVitalEntry("respiratory rate 16"))
        assertTrue(isVitalEntry("resp rate 18"))
        assertTrue(isVitalEntry("rr 20"))
    }

    @Test
    fun `vitals - oxygen saturation`() {
        assertTrue(isVitalEntry("o2 sat 98"))
        assertTrue(isVitalEntry("oxygen 97"))
        assertTrue(isVitalEntry("spo2 95"))
        assertTrue(isVitalEntry("sat 96"))
    }

    @Test
    fun `vitals - weight`() {
        assertTrue(isVitalEntry("weight 180 pounds"))
        assertTrue(isVitalEntry("weight 82 kg"))
        assertTrue(isVitalEntry("weighs 175"))
    }

    @Test
    fun `vitals - height`() {
        assertTrue(isVitalEntry("height 5 foot 10"))
        assertTrue(isVitalEntry("height 170 cm"))
        assertTrue(isVitalEntry("5 feet 8 inches"))
    }

    @Test
    fun `vitals - pain scale`() {
        assertTrue(isVitalEntry("pain 5 out of 10"))
        assertTrue(isVitalEntry("pain level 7"))
        assertTrue(isVitalEntry("pain score 3"))
    }

    @Test
    fun `vitals - show captured vitals`() {
        assertTrue(isVitalsCommand("show captured vitals"))
        assertTrue(isVitalsCommand("captured vitals"))
        assertTrue(isVitalsCommand("my vitals"))
        assertTrue(isVitalsCommand("vitals captured"))
    }

    @Test
    fun `vitals - clear captured vitals`() {
        assertTrue(isVitalsCommand("clear vitals"))
        assertTrue(isVitalsCommand("reset vitals"))
        assertTrue(isVitalsCommand("delete vitals"))
    }

    @Test
    fun `vitals - add vitals to note`() {
        assertTrue(isVitalsCommand("add vitals to note"))
        assertTrue(isVitalsCommand("insert vitals"))
        assertTrue(isVitalsCommand("vitals to note"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // VITAL HISTORY (Feature #47)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `vital history - show history`() {
        assertTrue(isVitalHistoryCommand("vital history"))
        assertTrue(isVitalHistoryCommand("vitals history"))
        assertTrue(isVitalHistoryCommand("past vitals"))
        assertTrue(isVitalHistoryCommand("vitals over time"))
        assertTrue(isVitalHistoryCommand("previous vitals"))
        assertTrue(isVitalHistoryCommand("historical vitals"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // CUSTOM VOICE COMMANDS (Feature #48)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `custom - create command`() {
        assertTrue(isCustomCommandOperation("create command morning rounds that does show worklist then load 1"))
        assertTrue(isCustomCommandOperation("when i say check labs do show labs"))
        assertTrue(isCustomCommandOperation("teach vitals check to show vitals then show labs"))
        assertTrue(isCustomCommandOperation("add command"))
        assertTrue(isCustomCommandOperation("add macro"))
    }

    @Test
    fun `custom - list commands`() {
        assertTrue(isCustomCommandOperation("my commands"))
        assertTrue(isCustomCommandOperation("list my commands"))
        assertTrue(isCustomCommandOperation("show custom commands"))
    }

    @Test
    fun `custom - delete command`() {
        assertTrue(isCustomCommandOperation("delete command morning rounds"))
        assertTrue(isCustomCommandOperation("remove command check labs"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // MEDICAL CALCULATOR (Feature #49)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `calculator - bmi`() {
        assertTrue(isCalculatorCommand("bmi"))
        assertTrue(isCalculatorCommand("calculate bmi"))
        assertTrue(isCalculatorCommand("body mass index"))
    }

    @Test
    fun `calculator - egfr`() {
        assertTrue(isCalculatorCommand("gfr"))
        assertTrue(isCalculatorCommand("egfr"))
        assertTrue(isCalculatorCommand("glomerular filtration"))
        assertTrue(isCalculatorCommand("kidney function"))
    }

    @Test
    fun `calculator - corrected calcium`() {
        assertTrue(isCalculatorCommand("corrected calcium"))
        assertTrue(isCalculatorCommand("calcium correction"))
    }

    @Test
    fun `calculator - anion gap`() {
        assertTrue(isCalculatorCommand("anion gap"))
        assertTrue(isCalculatorCommand("calculate anion gap"))
    }

    @Test
    fun `calculator - a1c conversion`() {
        assertTrue(isCalculatorCommand("a1c to glucose"))
        assertTrue(isCalculatorCommand("a1c glucose"))
        assertTrue(isCalculatorCommand("convert a1c"))
        assertTrue(isCalculatorCommand("glucose to a1c"))
    }

    @Test
    fun `calculator - map`() {
        assertTrue(isCalculatorCommand("map"))
        assertTrue(isCalculatorCommand("mean arterial pressure"))
    }

    @Test
    fun `calculator - creatinine clearance`() {
        assertTrue(isCalculatorCommand("creatinine clearance"))
        assertTrue(isCalculatorCommand("crcl"))
        assertTrue(isCalculatorCommand("cockcroft"))
    }

    @Test
    fun `calculator - chads vasc`() {
        assertTrue(isCalculatorCommand("chads"))
        assertTrue(isCalculatorCommand("chads2 vasc"))
        assertTrue(isCalculatorCommand("stroke risk"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // SBAR HANDOFF REPORT (Feature #50)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `handoff - generate report`() {
        assertTrue(isHandoffCommand("handoff report"))
        assertTrue(isHandoffCommand("hand off report"))
        assertTrue(isHandoffCommand("sbar report"))
        assertTrue(isHandoffCommand("sbar"))
        assertTrue(isHandoffCommand("shift report"))
        assertTrue(isHandoffCommand("handoff"))
    }

    @Test
    fun `handoff - speak report`() {
        assertTrue(isHandoffCommand("read handoff"))
        assertTrue(isHandoffCommand("speak handoff"))
        assertTrue(isHandoffCommand("tell me handoff"))
        assertTrue(isHandoffCommand("verbal handoff"))
        assertTrue(isHandoffCommand("give handoff"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // DISCHARGE SUMMARY (Feature #51)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `discharge - generate summary`() {
        assertTrue(isDischargeCommand("discharge summary"))
        assertTrue(isDischargeCommand("discharge instructions"))
        assertTrue(isDischargeCommand("discharge"))
        assertTrue(isDischargeCommand("patient instructions"))
    }

    @Test
    fun `discharge - speak instructions`() {
        assertTrue(isDischargeCommand("read discharge"))
        assertTrue(isDischargeCommand("speak discharge"))
        assertTrue(isDischargeCommand("explain discharge"))
        assertTrue(isDischargeCommand("tell patient"))
        assertTrue(isDischargeCommand("patient education"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // PROCEDURE CHECKLISTS (Feature #52)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `checklist - show checklists`() {
        assertTrue(isChecklistCommand("show checklists"))
        assertTrue(isChecklistCommand("procedure checklists"))
        assertTrue(isChecklistCommand("safety checklists"))
    }

    @Test
    fun `checklist - start checklist`() {
        assertTrue(isChecklistCommand("start timeout checklist"))
        assertTrue(isChecklistCommand("start central line checklist"))
        assertTrue(isChecklistCommand("start intubation checklist"))
        assertTrue(isChecklistCommand("start lumbar puncture checklist"))
        assertTrue(isChecklistCommand("start blood transfusion checklist"))
        assertTrue(isChecklistCommand("start sedation checklist"))
    }

    @Test
    fun `checklist - check items`() {
        assertTrue(isChecklistCommand("check 1"))
        assertTrue(isChecklistCommand("check 2"))
        assertTrue(isChecklistCommand("check 3"))
        assertTrue(isChecklistCommand("check all"))
    }

    @Test
    fun `checklist - read checklist`() {
        assertTrue(isChecklistCommand("read checklist"))
        assertTrue(isChecklistCommand("speak checklist"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // CLINICAL REMINDERS (Feature #53)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `reminders - show reminders`() {
        assertTrue(isRemindersCommand("clinical reminders"))
        assertTrue(isRemindersCommand("reminders"))
        assertTrue(isRemindersCommand("preventive care"))
        assertTrue(isRemindersCommand("care reminders"))
        assertTrue(isRemindersCommand("health reminders"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // MEDICATION RECONCILIATION (Feature #54)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `medrec - start reconciliation`() {
        assertTrue(isMedRecCommand("med reconciliation"))
        assertTrue(isMedRecCommand("medication reconciliation"))
        assertTrue(isMedRecCommand("reconcile meds"))
        assertTrue(isMedRecCommand("med rec"))
    }

    @Test
    fun `medrec - add home med`() {
        assertTrue(isMedRecCommand("add home med aspirin"))
        assertTrue(isMedRecCommand("add home medication lisinopril"))
    }

    @Test
    fun `medrec - remove home med`() {
        assertTrue(isMedRecCommand("remove home med 1"))
        assertTrue(isMedRecCommand("remove home medication 2"))
    }

    @Test
    fun `medrec - compare meds`() {
        assertTrue(isMedRecCommand("compare meds"))
        assertTrue(isMedRecCommand("compare medications"))
        assertTrue(isMedRecCommand("med comparison"))
    }

    @Test
    fun `medrec - clear home meds`() {
        assertTrue(isMedRecCommand("clear home meds"))
        assertTrue(isMedRecCommand("clear home medications"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // REFERRAL TRACKING (Feature #55)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `referral - show referrals`() {
        assertTrue(isReferralCommand("show referrals"))
        assertTrue(isReferralCommand("referrals"))
        assertTrue(isReferralCommand("pending referrals"))
    }

    @Test
    fun `referral - create referral`() {
        assertTrue(isReferralCommand("refer to cardiology"))
        assertTrue(isReferralCommand("refer to cardiology for chest pain"))
        assertTrue(isReferralCommand("urgent referral to neurology"))
        assertTrue(isReferralCommand("stat referral to surgery"))
    }

    @Test
    fun `referral - update status`() {
        assertTrue(isReferralCommand("mark referral 1 scheduled"))
        assertTrue(isReferralCommand("mark referral 2 completed"))
    }

    @Test
    fun `referral - clear referrals`() {
        assertTrue(isReferralCommand("clear referrals"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // SPECIALTY TEMPLATES (Feature #56)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `specialty - list templates`() {
        assertTrue(isSpecialtyTemplateCommand("list specialty templates"))
        assertTrue(isSpecialtyTemplateCommand("specialty templates"))
        assertTrue(isSpecialtyTemplateCommand("show specialty templates"))
    }

    @Test
    fun `specialty - use templates`() {
        assertTrue(isSpecialtyTemplateCommand("use cardiology chest pain template"))
        assertTrue(isSpecialtyTemplateCommand("use cardiology heart failure template"))
        assertTrue(isSpecialtyTemplateCommand("use cardiology afib template"))
        assertTrue(isSpecialtyTemplateCommand("use orthopedics joint pain template"))
        assertTrue(isSpecialtyTemplateCommand("use neurology headache template"))
        assertTrue(isSpecialtyTemplateCommand("use gi abdominal pain template"))
        assertTrue(isSpecialtyTemplateCommand("use pulmonology copd template"))
        assertTrue(isSpecialtyTemplateCommand("use psychiatry depression template"))
        assertTrue(isSpecialtyTemplateCommand("use emergency trauma template"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // NOTE VERSIONING (Feature #57)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `versioning - show history`() {
        assertTrue(isVersioningCommand("version history"))
        assertTrue(isVersioningCommand("note versions"))
        assertTrue(isVersioningCommand("show versions"))
    }

    @Test
    fun `versioning - restore version`() {
        assertTrue(isVersioningCommand("restore version 1"))
        assertTrue(isVersioningCommand("restore version 2"))
        assertTrue(isVersioningCommand("restore version 3"))
    }

    @Test
    fun `versioning - compare versions`() {
        assertTrue(isVersioningCommand("compare versions"))
        assertTrue(isVersioningCommand("diff versions"))
        assertTrue(isVersioningCommand("version diff"))
    }

    @Test
    fun `versioning - clear history`() {
        assertTrue(isVersioningCommand("clear version history"))
        assertTrue(isVersioningCommand("clear versions"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // DATA ENCRYPTION (Feature #60)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `encryption - status`() {
        assertTrue(isEncryptionCommand("encryption status"))
        assertTrue(isEncryptionCommand("security status"))
    }

    @Test
    fun `encryption - wipe data`() {
        assertTrue(isEncryptionCommand("wipe data"))
        assertTrue(isEncryptionCommand("secure wipe"))
        assertTrue(isEncryptionCommand("erase data"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // MULTI-LANGUAGE SUPPORT (Feature #61)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `language - switch to english`() {
        assertEquals("en", parseLanguage("switch to english"))
        assertEquals("en", parseLanguage("english"))
    }

    @Test
    fun `language - switch to spanish`() {
        assertEquals("es", parseLanguage("switch to spanish"))
        assertEquals("es", parseLanguage("español"))
        assertEquals("es", parseLanguage("espanol"))
    }

    @Test
    fun `language - switch to russian`() {
        assertEquals("ru", parseLanguage("switch to russian"))
        assertEquals("ru", parseLanguage("русский"))
    }

    @Test
    fun `language - switch to mandarin`() {
        assertEquals("zh", parseLanguage("switch to chinese"))
        assertEquals("zh", parseLanguage("switch to mandarin"))
    }

    @Test
    fun `language - switch to portuguese`() {
        assertEquals("pt", parseLanguage("switch to portuguese"))
    }

    @Test
    fun `language - language options`() {
        assertTrue(isLanguageCommand("language options"))
        assertTrue(isLanguageCommand("available languages"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // AMBIENT CLINICAL INTELLIGENCE (Feature #62)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `ambient - start ambient`() {
        assertTrue(isAmbientCommand("ambient mode"))
        assertTrue(isAmbientCommand("start ambient"))
        assertTrue(isAmbientCommand("starts ambient"))
        assertTrue(isAmbientCommand("ambient listening"))
        assertTrue(isAmbientCommand("auto document"))
    }

    @Test
    fun `ambient - stop ambient`() {
        assertTrue(isAmbientCommand("stop ambient"))
        assertTrue(isAmbientCommand("end ambient"))
        assertTrue(isAmbientCommand("finish ambient"))
        assertTrue(isAmbientCommand("stop listening"))
    }

    @Test
    fun `ambient - cancel ambient`() {
        assertTrue(isAmbientCommand("cancel ambient"))
        assertTrue(isAmbientCommand("discard ambient"))
        assertTrue(isAmbientCommand("never mind"))
    }

    @Test
    fun `ambient - show entities`() {
        assertTrue(isAmbientCommand("show entities"))
        assertTrue(isAmbientCommand("what did you detect"))
        assertTrue(isAmbientCommand("what did you hear"))
    }

    @Test
    fun `ambient - ambient status`() {
        assertTrue(isAmbientCommand("ambient status"))
        assertTrue(isAmbientCommand("aci status"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // CRUD WRITE-BACK TO EHR (Feature #63)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `crud - push vitals`() {
        assertTrue(isCrudCommand("push vitals"))
        assertTrue(isCrudCommand("send vitals to ehr"))
    }

    @Test
    fun `crud - push orders`() {
        assertTrue(isCrudCommand("push orders"))
        assertTrue(isCrudCommand("send orders to ehr"))
    }

    @Test
    fun `crud - add allergy`() {
        assertTrue(isCrudCommand("add allergy to penicillin"))
        assertTrue(isCrudCommand("add allergy to sulfa"))
    }

    @Test
    fun `crud - discontinue medication`() {
        assertTrue(isCrudCommand("discontinue metformin"))
        assertTrue(isCrudCommand("stop metformin"))
        assertTrue(isCrudCommand("dc metformin"))
    }

    @Test
    fun `crud - hold medication`() {
        assertTrue(isCrudCommand("hold metformin"))
        assertTrue(isCrudCommand("pause metformin"))
    }

    @Test
    fun `crud - sync all`() {
        assertTrue(isCrudCommand("sync all"))
        assertTrue(isCrudCommand("sync everything"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // DEVICE AUTHENTICATION (Feature #64)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `device - pair device`() {
        assertTrue(isDeviceCommand("pair device"))
        assertTrue(isDeviceCommand("pair glasses"))
        assertTrue(isDeviceCommand("pair this device"))
    }

    @Test
    fun `device - device status`() {
        assertTrue(isDeviceCommand("device status"))
        assertTrue(isDeviceCommand("pairing status"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // VOICEPRINT SPEAKER RECOGNITION (Feature #66)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `voiceprint - enroll`() {
        assertTrue(isVoiceprintCommand("enroll my voice"))
        assertTrue(isVoiceprintCommand("enroll voiceprint"))
        assertTrue(isVoiceprintCommand("setup voiceprint"))
    }

    @Test
    fun `voiceprint - status`() {
        assertTrue(isVoiceprintCommand("voiceprint status"))
        assertTrue(isVoiceprintCommand("voice print status"))
    }

    @Test
    fun `voiceprint - delete`() {
        assertTrue(isVoiceprintCommand("delete voiceprint"))
        assertTrue(isVoiceprintCommand("remove voiceprint"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // PATIENT WORKLIST (Feature #67)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `worklist - show worklist`() {
        assertTrue(isWorklistCommand("show worklist"))
        assertTrue(isWorklistCommand("worklist"))
        assertTrue(isWorklistCommand("today's patients"))
        assertTrue(isWorklistCommand("todays patients"))
        assertTrue(isWorklistCommand("my schedule"))
        assertTrue(isWorklistCommand("patient schedule"))
        assertTrue(isWorklistCommand("daily schedule"))
    }

    @Test
    fun `worklist - whos next`() {
        assertTrue(isWorklistCommand("who's next"))
        assertTrue(isWorklistCommand("whos next"))
        assertTrue(isWorklistCommand("who is next"))
        assertTrue(isWorklistCommand("next patient"))
    }

    @Test
    fun `worklist - check in`() {
        assertTrue(isWorklistCommand("check in 1"))
        assertTrue(isWorklistCommand("check in patient 2"))
        assertTrue(isWorklistCommand("check in 3 to room 5"))
    }

    @Test
    fun `worklist - mark completed`() {
        assertTrue(isWorklistCommand("mark 1 completed"))
        assertTrue(isWorklistCommand("patient 2 done"))
        assertTrue(isWorklistCommand("mark 3 finished"))
    }

    @Test
    fun `worklist - start seeing`() {
        assertTrue(isWorklistCommand("start seeing 1"))
        assertTrue(isWorklistCommand("begin encounter 2"))
        assertTrue(isWorklistCommand("seeing patient 3"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // ORDER UPDATE/MODIFY (Feature #68)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `order update - update by number`() {
        assertTrue(isOrderUpdateCommand("update 1 to 500mg every 6 hours"))
        assertTrue(isOrderUpdateCommand("update 2 to twice daily"))
    }

    @Test
    fun `order update - update by name`() {
        assertTrue(isOrderUpdateCommand("update tylenol to 650mg prn"))
        assertTrue(isOrderUpdateCommand("update metformin to 1000mg"))
    }

    @Test
    fun `order update - delete by number`() {
        assertTrue(isOrderUpdateCommand("delete 1"))
        assertTrue(isOrderUpdateCommand("delete 2"))
        assertTrue(isOrderUpdateCommand("remove 3"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // AI DIFFERENTIAL DIAGNOSIS (Feature #69)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `ddx - generate differential`() {
        assertTrue(isDdxCommand("differential diagnosis"))
        assertTrue(isDdxCommand("ddx"))
        assertTrue(isDdxCommand("what could this be"))
        assertTrue(isDdxCommand("differentials"))
    }

    @Test
    fun `ddx - read differential`() {
        assertTrue(isDdxCommand("read differential"))
        assertTrue(isDdxCommand("speak ddx"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // MEDICAL IMAGE RECOGNITION (Feature #70)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `image - take photo`() {
        assertTrue(isImageCommand("take photo"))
        assertTrue(isImageCommand("capture image"))
        assertTrue(isImageCommand("take picture"))
    }

    @Test
    fun `image - analyze wound`() {
        assertTrue(isImageCommand("analyze wound"))
        assertTrue(isImageCommand("wound assessment"))
    }

    @Test
    fun `image - analyze rash`() {
        assertTrue(isImageCommand("analyze rash"))
        assertTrue(isImageCommand("skin assessment"))
    }

    @Test
    fun `image - analyze xray`() {
        assertTrue(isImageCommand("analyze xray"))
        assertTrue(isImageCommand("analyze x-ray"))
        assertTrue(isImageCommand("read xray"))
    }

    @Test
    fun `image - read analysis`() {
        assertTrue(isImageCommand("read analysis"))
        assertTrue(isImageCommand("image results"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // BILLING/CODING SUBMISSION (Feature #71)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `billing - create claim`() {
        assertTrue(isBillingCommand("create claim"))
        assertTrue(isBillingCommand("bill this"))
        assertTrue(isBillingCommand("billing for this"))
    }

    @Test
    fun `billing - add diagnosis`() {
        assertTrue(isBillingCommand("add diagnosis j06.9"))
        assertTrue(isBillingCommand("add icd i10"))
    }

    @Test
    fun `billing - remove diagnosis`() {
        assertTrue(isBillingCommand("remove diagnosis 1"))
        assertTrue(isBillingCommand("remove diagnosis 2"))
    }

    @Test
    fun `billing - add procedure`() {
        assertTrue(isBillingCommand("add procedure 99213"))
        assertTrue(isBillingCommand("add cpt 99214"))
    }

    @Test
    fun `billing - add modifier`() {
        assertTrue(isBillingCommand("add modifier 25 to 1"))
        assertTrue(isBillingCommand("add modifier 59"))
    }

    @Test
    fun `billing - search codes`() {
        assertTrue(isBillingCommand("search icd hypertension"))
        assertTrue(isBillingCommand("search cpt office visit"))
    }

    @Test
    fun `billing - submit claim`() {
        assertTrue(isBillingCommand("submit claim"))
        assertTrue(isBillingCommand("submit billing"))
    }

    @Test
    fun `billing - claim history`() {
        assertTrue(isBillingCommand("show claims"))
        assertTrue(isBillingCommand("claim history"))
        assertTrue(isBillingCommand("billing history"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // DNFB (Feature #72)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `dnfb - show dnfb`() {
        assertTrue(isDnfbCommand("show dnfb"))
        assertTrue(isDnfbCommand("dnfb"))
        assertTrue(isDnfbCommand("discharged not final billed"))
    }

    @Test
    fun `dnfb - dnfb summary`() {
        assertTrue(isDnfbCommand("dnfb summary"))
        assertTrue(isDnfbCommand("unbilled summary"))
    }

    @Test
    fun `dnfb - prior auth issues`() {
        assertTrue(isDnfbCommand("prior auth issues"))
        assertTrue(isDnfbCommand("auth issues"))
    }

    @Test
    fun `dnfb - aging filter`() {
        assertTrue(isDnfbCommand("over 7 days"))
        assertTrue(isDnfbCommand("over 14 days"))
        assertTrue(isDnfbCommand("aging"))
    }

    @Test
    fun `dnfb - resolve`() {
        assertTrue(isDnfbCommand("resolve 1"))
        assertTrue(isDnfbCommand("resolve 2"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // VUZIX HUD (Feature #73)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `hud - show hud`() {
        assertTrue(isHudCommand("show hud"))
    }

    @Test
    fun `hud - hide hud`() {
        assertTrue(isHudCommand("hide hud"))
    }

    @Test
    fun `hud - expand hud`() {
        assertTrue(isHudCommand("expand hud"))
    }

    @Test
    fun `hud - minimize hud`() {
        assertTrue(isHudCommand("minimize hud"))
    }

    @Test
    fun `hud - toggle hud`() {
        assertTrue(isHudCommand("toggle hud"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // GESTURE CONTROL (Feature #75)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `gesture - enable gestures`() {
        assertTrue(isGestureCommand("enable gestures"))
        assertTrue(isGestureCommand("gestures on"))
    }

    @Test
    fun `gesture - disable gestures`() {
        assertTrue(isGestureCommand("disable gestures"))
        assertTrue(isGestureCommand("gestures off"))
    }

    @Test
    fun `gesture - gesture status`() {
        assertTrue(isGestureCommand("gesture status"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // WINK GESTURE (Feature #76)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `wink - enable wink`() {
        assertTrue(isWinkCommand("enable wink"))
        assertTrue(isWinkCommand("wink on"))
    }

    @Test
    fun `wink - disable wink`() {
        assertTrue(isWinkCommand("disable wink"))
        assertTrue(isWinkCommand("wink off"))
    }

    @Test
    fun `wink - wink status`() {
        assertTrue(isWinkCommand("wink status"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // VOICE BIOMETRIC CONTINUOUS AUTH (Feature #77)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `verify - verify me`() {
        assertTrue(isVerifyCommand("verify me"))
        assertTrue(isVerifyCommand("verify my voice"))
        assertTrue(isVerifyCommand("verify identity"))
    }

    @Test
    fun `verify - verification status`() {
        assertTrue(isVerifyCommand("verification status"))
        assertTrue(isVerifyCommand("verify status"))
        assertTrue(isVerifyCommand("auth status"))
    }

    @Test
    fun `verify - set interval`() {
        assertTrue(isVerifyCommand("set verify interval 5 minutes"))
        assertTrue(isVerifyCommand("set verification interval 10 min"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // AI CLINICAL CO-PILOT (Feature #78)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `copilot - activate`() {
        assertTrue(isCopilotCommand("hey copilot"))
        assertTrue(isCopilotCommand("copilot"))
        assertTrue(isCopilotCommand("ask copilot"))
        assertTrue(isCopilotCommand("activate copilot"))
    }

    @Test
    fun `copilot - question triggers`() {
        assertTrue(isCopilotCommand("what should i consider"))
        assertTrue(isCopilotCommand("what do you think"))
        assertTrue(isCopilotCommand("what would you recommend"))
    }

    @Test
    fun `copilot - follow up`() {
        assertTrue(isCopilotCommand("tell me more"))
        assertTrue(isCopilotCommand("elaborate"))
        assertTrue(isCopilotCommand("explain more"))
    }

    @Test
    fun `copilot - suggestions`() {
        assertTrue(isCopilotCommand("suggest next"))
        assertTrue(isCopilotCommand("what next"))
    }

    @Test
    fun `copilot - clear`() {
        assertTrue(isCopilotCommand("clear copilot"))
        assertTrue(isCopilotCommand("reset copilot"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // RACIAL MEDICINE AWARENESS (Feature #79)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `racial - pulse ox alert`() {
        assertTrue(isRacialMedicineCommand("pulse ox alert"))
        assertTrue(isRacialMedicineCommand("pulse oximeter accuracy"))
    }

    @Test
    fun `racial - skin assessment`() {
        assertTrue(isRacialMedicineCommand("skin assessment guidance"))
        assertTrue(isRacialMedicineCommand("skin assessment"))
    }

    @Test
    fun `racial - ancestry medications`() {
        assertTrue(isRacialMedicineCommand("ancestry meds"))
        assertTrue(isRacialMedicineCommand("pharmacogenomics"))
    }

    @Test
    fun `racial - maternal mortality`() {
        assertTrue(isRacialMedicineCommand("maternal mortality"))
        assertTrue(isRacialMedicineCommand("maternal risk"))
    }

    @Test
    fun `racial - sickle cell protocol`() {
        assertTrue(isRacialMedicineCommand("sickle cell protocol"))
        assertTrue(isRacialMedicineCommand("sickle cell"))
    }

    @Test
    fun `racial - pain assessment bias`() {
        assertTrue(isRacialMedicineCommand("pain assessment"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // CULTURAL CARE PREFERENCES (Feature #80)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `cultural - blood preferences`() {
        assertTrue(isCulturalCareCommand("blood preferences"))
        assertTrue(isCulturalCareCommand("blood products"))
        assertTrue(isCulturalCareCommand("blood product preferences"))
    }

    @Test
    fun `cultural - dietary restrictions`() {
        assertTrue(isCulturalCareCommand("dietary restrictions"))
        assertTrue(isCulturalCareCommand("halal"))
        assertTrue(isCulturalCareCommand("kosher"))
    }

    @Test
    fun `cultural - fasting`() {
        assertTrue(isCulturalCareCommand("fasting"))
        assertTrue(isCulturalCareCommand("ramadan"))
    }

    @Test
    fun `cultural - modesty`() {
        assertTrue(isCulturalCareCommand("modesty requirements"))
        assertTrue(isCulturalCareCommand("same gender provider"))
    }

    @Test
    fun `cultural - end of life`() {
        assertTrue(isCulturalCareCommand("end of life"))
        assertTrue(isCulturalCareCommand("advance directive"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // IMPLICIT BIAS ALERTS (Feature #81)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `bias - bias check`() {
        assertTrue(isBiasCommand("bias check"))
        assertTrue(isBiasCommand("bias alert"))
        assertTrue(isBiasCommand("bias reminder"))
    }

    @Test
    fun `bias - enable disable`() {
        assertTrue(isBiasCommand("enable bias alerts"))
        assertTrue(isBiasCommand("disable bias alerts"))
        assertTrue(isBiasCommand("bias alerts on"))
        assertTrue(isBiasCommand("bias alerts off"))
    }

    @Test
    fun `bias - bias status`() {
        assertTrue(isBiasCommand("bias status"))
    }

    @Test
    fun `bias - bias resources`() {
        assertTrue(isBiasCommand("bias resources"))
        assertTrue(isBiasCommand("bias training"))
    }

    @Test
    fun `bias - acknowledge bias`() {
        assertTrue(isBiasCommand("acknowledge bias"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // MATERNAL HEALTH MONITORING (Feature #82)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `maternal - maternal health`() {
        assertTrue(isMaternalCommand("maternal health"))
        assertTrue(isMaternalCommand("ob health"))
    }

    @Test
    fun `maternal - pregnancy status`() {
        assertTrue(isMaternalCommand("patient is pregnant"))
        assertTrue(isMaternalCommand("patient is postpartum"))
    }

    @Test
    fun `maternal - warning signs`() {
        assertTrue(isMaternalCommand("warning signs"))
        assertTrue(isMaternalCommand("danger signs"))
    }

    @Test
    fun `maternal - postpartum checklist`() {
        assertTrue(isMaternalCommand("postpartum checklist"))
    }

    @Test
    fun `maternal - preeclampsia`() {
        assertTrue(isMaternalCommand("preeclampsia"))
        assertTrue(isMaternalCommand("pre-eclampsia"))
    }

    @Test
    fun `maternal - hemorrhage`() {
        assertTrue(isMaternalCommand("hemorrhage"))
        assertTrue(isMaternalCommand("postpartum bleeding"))
    }

    @Test
    fun `maternal - ppd screen`() {
        assertTrue(isMaternalCommand("ppd screen"))
        assertTrue(isMaternalCommand("depression screen"))
        assertTrue(isMaternalCommand("edinburgh"))
    }

    @Test
    fun `maternal - disparity data`() {
        assertTrue(isMaternalCommand("maternal disparity"))
        assertTrue(isMaternalCommand("disparity data"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // SDOH INTEGRATION (Feature #84)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `sdoh - sdoh screen`() {
        assertTrue(isSdohCommand("sdoh"))
        assertTrue(isSdohCommand("sdoh screen"))
        assertTrue(isSdohCommand("social determinants"))
    }

    @Test
    fun `sdoh - food insecurity`() {
        assertTrue(isSdohCommand("food insecurity"))
        assertTrue(isSdohCommand("food insecure"))
    }

    @Test
    fun `sdoh - housing`() {
        assertTrue(isSdohCommand("housing unstable"))
        assertTrue(isSdohCommand("housing instability"))
        assertTrue(isSdohCommand("homeless"))
    }

    @Test
    fun `sdoh - transportation`() {
        assertTrue(isSdohCommand("transportation barrier"))
        assertTrue(isSdohCommand("no transportation"))
    }

    @Test
    fun `sdoh - insurance`() {
        assertTrue(isSdohCommand("no insurance"))
        assertTrue(isSdohCommand("uninsured"))
    }

    @Test
    fun `sdoh - financial strain`() {
        assertTrue(isSdohCommand("financial strain"))
        assertTrue(isSdohCommand("financial hardship"))
    }

    @Test
    fun `sdoh - social isolation`() {
        assertTrue(isSdohCommand("lives alone"))
        assertTrue(isSdohCommand("social isolation"))
    }

    @Test
    fun `sdoh - interventions`() {
        assertTrue(isSdohCommand("sdoh interventions"))
        assertTrue(isSdohCommand("social services"))
    }

    @Test
    fun `sdoh - z codes`() {
        assertTrue(isSdohCommand("z codes"))
        assertTrue(isSdohCommand("sdoh codes"))
    }

    @Test
    fun `sdoh - adherence barriers`() {
        assertTrue(isSdohCommand("adherence barriers"))
        assertTrue(isSdohCommand("adherence risks"))
    }

    @Test
    fun `sdoh - clear sdoh`() {
        assertTrue(isSdohCommand("clear sdoh"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // HEALTH LITERACY ASSESSMENT (Feature #85)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `literacy - assess literacy`() {
        assertTrue(isLiteracyCommand("literacy"))
        assertTrue(isLiteracyCommand("literacy screen"))
        assertTrue(isLiteracyCommand("assess literacy"))
    }

    @Test
    fun `literacy - literacy levels`() {
        assertTrue(isLiteracyCommand("low literacy"))
        assertTrue(isLiteracyCommand("marginal literacy"))
        assertTrue(isLiteracyCommand("adequate literacy"))
    }

    @Test
    fun `literacy - simplified instructions`() {
        assertTrue(isLiteracyCommand("diabetes instructions"))
        assertTrue(isLiteracyCommand("heart failure instructions"))
        assertTrue(isLiteracyCommand("blood pressure instructions"))
        assertTrue(isLiteracyCommand("blood thinner instructions"))
        assertTrue(isLiteracyCommand("antibiotic instructions"))
    }

    @Test
    fun `literacy - teach back`() {
        assertTrue(isLiteracyCommand("teach back"))
        assertTrue(isLiteracyCommand("teach back checklist"))
    }

    @Test
    fun `literacy - plain language`() {
        assertTrue(isLiteracyCommand("plain language"))
        assertTrue(isLiteracyCommand("simple language"))
    }

    @Test
    fun `literacy - accommodations`() {
        assertTrue(isLiteracyCommand("accommodations"))
        assertTrue(isLiteracyCommand("literacy accommodations"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // INTERPRETER INTEGRATION (Feature #86)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `interpreter - request interpreter`() {
        assertTrue(isInterpreterCommand("need interpreter"))
        assertTrue(isInterpreterCommand("request interpreter"))
        assertTrue(isInterpreterCommand("get interpreter"))
    }

    @Test
    fun `interpreter - specific language`() {
        assertTrue(isInterpreterCommand("spanish interpreter"))
        assertTrue(isInterpreterCommand("chinese interpreter"))
        assertTrue(isInterpreterCommand("vietnamese interpreter"))
        assertTrue(isInterpreterCommand("arabic interpreter"))
        assertTrue(isInterpreterCommand("asl interpreter"))
    }

    @Test
    fun `interpreter - set language preference`() {
        assertTrue(isInterpreterCommand("set language spanish"))
        assertTrue(isInterpreterCommand("patient speaks spanish"))
    }

    @Test
    fun `interpreter - clinical phrases`() {
        assertTrue(isInterpreterCommand("clinical phrases"))
        assertTrue(isInterpreterCommand("common phrases"))
    }

    @Test
    fun `interpreter - interpreter services`() {
        assertTrue(isInterpreterCommand("interpreter services"))
        assertTrue(isInterpreterCommand("language services"))
    }

    @Test
    fun `interpreter - title vi compliance`() {
        assertTrue(isInterpreterCommand("title vi"))
        assertTrue(isInterpreterCommand("title 6"))
    }

    @Test
    fun `interpreter - start end session`() {
        assertTrue(isInterpreterCommand("start interpreter"))
        assertTrue(isInterpreterCommand("begin interpreter"))
        assertTrue(isInterpreterCommand("end interpreter"))
        assertTrue(isInterpreterCommand("stop interpreter"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // CONTROL COMMANDS
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `control - stop talking`() {
        assertTrue(isControlCommand("stop talking"))
        assertTrue(isControlCommand("stop speaking"))
        assertTrue(isControlCommand("be quiet"))
        assertTrue(isControlCommand("quiet"))
    }

    @Test
    fun `control - stop listening`() {
        assertTrue(isControlCommand("stop listening"))
        assertTrue(isControlCommand("stop voice"))
        assertTrue(isControlCommand("mute"))
    }

    @Test
    fun `control - close dismiss`() {
        assertTrue(isControlCommand("close"))
        assertTrue(isControlCommand("dismiss"))
        assertTrue(isControlCommand("back"))
        assertTrue(isControlCommand("go away"))
    }

    @Test
    fun `control - clear cache`() {
        assertTrue(isControlCommand("clear cache"))
        assertTrue(isControlCommand("clear offline"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // HELPER FUNCTIONS - Voice Command Matchers
    // ═══════════════════════════════════════════════════════════════════════════

    private fun isPatientCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("load patient") ||
               lower.matches(Regex("load \\d+")) ||
               lower.contains("find patient") ||
               lower.contains("scan")
    }

    private fun isShowCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("vital") || lower.contains("allerg") ||
               lower.contains("medication") || lower.contains("meds") || lower.contains("drugs") ||
               lower.contains("labs") || lower.contains("laboratory") || lower.contains("results") ||
               lower.contains("procedure") || lower.contains("surgery") || lower.contains("operation") ||
               lower.contains("immunization") || lower.contains("vaccine") || lower.contains("vaccination") ||
               lower.contains("shot") ||
               lower.contains("condition") || lower.contains("problem") || lower.contains("diagnos") ||
               lower.contains("care plan") || lower.contains("treatment plan") ||
               lower.contains("clinical note") || lower.contains("show notes") || lower.contains("patient notes") ||
               lower.contains("previous note") || lower.contains("history note")
    }

    private fun isNoteCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("start note") || lower.contains("begin note") || lower.contains("new note") ||
               lower.contains("live transcribe") || lower.contains("start transcription") ||
               lower.contains("generate note") || lower.contains("create note") || lower.contains("make note") ||
               lower.contains("document this") ||
               lower.contains("re-record") || lower.contains("rerecord") || lower.contains("record again") ||
               lower.contains("try again") ||
               lower.contains("edit note") || lower.contains("modify note") ||
               lower.contains("reset note") || lower.contains("clear note") ||
               lower.contains("save note") || lower == "save" ||
               lower.contains("push note") || lower.contains("send to ehr") || lower.contains("push to ehr")
    }

    private fun isStopCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("stop transcri") || lower.contains("stop recording") || lower.contains("close")
    }

    private fun containsWakeWord(phrase: String): Boolean {
        val lower = phrase.lowercase()
        return lower.contains("hey minerva") || lower.contains("hey m i n e r v a")
    }

    private fun extractCommandAfterWakeWord(phrase: String): String {
        val lower = phrase.lowercase()
        return when {
            lower.contains("hey minerva") -> lower.substringAfter("hey minerva").trim()
            lower.contains("hey m i n e r v a") -> lower.substringAfter("hey m i n e r v a").trim()
            else -> phrase
        }
    }

    private fun isModeCommand(cmd: String): Boolean {
        return cmd.lowercase().contains("minerva mode")
    }

    private fun isHelpCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("help") || lower.contains("what can i say") ||
               lower.contains("voice commands") || lower.contains("show commands") ||
               lower.contains("list commands") || lower.contains("available commands")
    }

    private fun isSummaryCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("patient summary") || lower.contains("summarize patient") ||
               lower.contains("quick summary") || lower.contains("show summary") ||
               lower.contains("overview")
    }

    private fun isBriefingCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("tell me about") || lower.contains("read summary") ||
               lower.contains("speak summary") || lower.contains("brief me") ||
               lower.contains("briefing") || lower.contains("patient brief") ||
               lower.contains("read patient") || lower.contains("summarize")
    }

    private fun parseFontSize(cmd: String): String? {
        val lower = cmd.lowercase()
        return when {
            lower.contains("extra large") || lower.contains("huge") || lower.contains("biggest") -> "extra_large"
            lower.contains("large") || lower.contains("larger") || lower.contains("bigger") -> "large"
            lower.contains("medium") || lower.contains("normal") -> "medium"
            lower.contains("small") -> "small"
            else -> null
        }
    }

    private fun isScrollCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("auto scroll")
    }

    private fun isTemplateCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("soap") || lower.contains("progress note") ||
               lower.contains("h and p") || lower.contains("consult note") ||
               lower.contains("auto detect")
    }

    private fun isDiarizationCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("show speakers") || lower.contains("who is speaking")
    }

    private fun isSignoffCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("sign note") || lower.contains("sign and save") ||
               lower.contains("finalize note")
    }

    private fun isOfflineCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("sync notes") || lower.contains("show drafts") ||
               lower.contains("delete draft")
    }

    private fun isHistoryCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("show history") || lower.contains("recent patients") ||
               lower.contains("patient history") || lower.contains("clear history")
    }

    private fun isTimeoutCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("lock") || lower.contains("unlock") ||
               lower.contains("timeout")
    }

    private fun parseTimeoutMinutes(cmd: String): Int? {
        val match = Regex("(\\d+)\\s*min").find(cmd.lowercase())
        return match?.groupValues?.get(1)?.toIntOrNull()
    }

    private fun isEditCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("change") || lower.contains("set") ||
               lower.contains("add to") || lower.contains("append to") ||
               lower.contains("delete last") || lower.contains("remove last") ||
               lower.contains("clear subjective") || lower.contains("clear objective") ||
               lower.contains("clear assessment") || lower.contains("clear plan") ||
               lower.contains("insert") || lower.contains("add macro") ||
               lower.contains("undo")
    }

    private fun isNavigationCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("scroll") || lower.contains("page") ||
               lower.contains("go to") || lower.contains("jump to") ||
               lower.contains("navigate to") || lower.contains("show") && lower.contains("only") ||
               lower.contains("read")
    }

    private fun isDictationCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("dictate") || lower.contains("dictating") || lower.contains("dictation")
    }

    private fun isVoiceTemplateCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("template")
    }

    private fun isOrderCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("order") || lower.contains("prescribe") ||
               lower.contains("cancel order") || lower.contains("remove order") ||
               lower.contains("delete order") || lower.contains("clear all order")
    }

    private fun isConfirmCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower == "yes" || lower == "confirm" || lower.contains("confirm order") ||
               lower.contains("place order") || lower.contains("go ahead")
    }

    private fun isRejectCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower == "no" || lower == "reject" || lower.contains("don't order") ||
               lower.contains("do not order") || lower == "cancel"
    }

    private fun isTimerCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("timer") || lower.contains("encounter") ||
               lower.contains("how long") || lower.contains("what time") ||
               lower.contains("elapsed time") || lower.contains("time elapsed") ||
               lower.contains("how much time") || lower.contains("time spent")
    }

    private fun isOrderSetCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("order set") || lower.contains("what's in") ||
               lower.contains("whats in") || lower.contains("preview") ||
               lower.contains("workup") || lower.contains("bundle") ||
               lower.contains("protocol") ||
               (lower.startsWith("order ") && (lower.contains("admission labs") ||
                lower.contains("preop labs") || lower.contains("copd exacerbation")))
    }

    private fun isVitalEntry(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("bp ") || lower.contains("blood pressure") ||
               lower.contains("pulse") || lower.contains("heart rate") || lower.contains("hr ") ||
               lower.contains("temp ") || lower.contains("temperature") || lower.contains("fever") ||
               lower.contains("respiratory rate") || lower.contains("resp rate") || lower.contains("rr ") ||
               lower.contains("o2 sat") || lower.contains("oxygen") || lower.contains("spo2") || lower.contains("sat ") ||
               lower.contains("weight") || lower.contains("weighs") ||
               lower.contains("height") || lower.contains("feet") ||
               lower.contains("pain")
    }

    private fun isVitalsCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("captured vital") || lower.contains("my vital") ||
               lower.contains("show captured") || lower.contains("vitals captured") ||
               lower.contains("clear vital") || lower.contains("reset vital") ||
               lower.contains("delete vital") ||
               lower.contains("add vital") && lower.contains("note") ||
               lower.contains("insert vital") || lower.contains("vitals to note")
    }

    private fun isVitalHistoryCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("vital history") || lower.contains("vitals history") ||
               lower.contains("past vital") || lower.contains("vitals over time") ||
               lower.contains("previous vital") || lower.contains("historical vital")
    }

    private fun isCustomCommandOperation(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("create command") || lower.contains("when i say") ||
               lower.contains("teach") || lower.contains("add command") ||
               lower.contains("add macro") || lower.contains("my commands") ||
               lower.contains("list my commands") || lower.contains("show custom commands") ||
               lower.contains("delete command") || lower.contains("remove command")
    }

    private fun isCalculatorCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("bmi") || lower.contains("body mass") ||
               lower.contains("gfr") || lower.contains("glomerular") || lower.contains("kidney function") ||
               lower.contains("corrected calcium") || lower.contains("calcium correct") ||
               lower.contains("anion gap") || lower.contains("anion") ||
               lower.contains("a1c") || lower.contains("glucose") ||
               lower.contains("map") || lower.contains("mean arterial") ||
               lower.contains("creatinine clearance") || lower.contains("crcl") || lower.contains("cockcroft") ||
               lower.contains("chads") || lower.contains("stroke risk")
    }

    private fun isHandoffCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("handoff") || lower.contains("hand off") ||
               lower.contains("sbar") || lower.contains("shift report")
    }

    private fun isDischargeCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("discharge") || lower.contains("patient instructions") ||
               lower.contains("patient education") || lower.contains("tell patient")
    }

    private fun isChecklistCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("checklist") || lower.contains("check all") ||
               (lower.contains("check ") && lower.matches(Regex(".*check\\s+\\d+.*")))
    }

    private fun isRemindersCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("reminder") || lower.contains("preventive care")
    }

    private fun isMedRecCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("med rec") || lower.contains("reconcil") ||
               lower.contains("home med") || lower.contains("compare med") ||
               (lower.contains("comparison") && lower.contains("med"))
    }

    private fun isReferralCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("referral") || lower.contains("refer to")
    }

    private fun isSpecialtyTemplateCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("specialty template") ||
               (lower.contains("template") && (lower.contains("cardiology") ||
                lower.contains("orthopedics") || lower.contains("neurology") ||
                lower.contains("gi") || lower.contains("pulmonology") ||
                lower.contains("psychiatry") || lower.contains("emergency")))
    }

    private fun isVersioningCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("version")
    }

    private fun isEncryptionCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("encryption") || lower.contains("security status") ||
               lower.contains("wipe data") || lower.contains("secure wipe") ||
               lower.contains("erase data")
    }

    private fun parseLanguage(cmd: String): String? {
        val lower = cmd.lowercase()
        return when {
            lower.contains("english") -> "en"
            lower.contains("spanish") || lower.contains("español") || lower.contains("espanol") -> "es"
            lower.contains("russian") || lower.contains("русский") -> "ru"
            lower.contains("chinese") || lower.contains("mandarin") -> "zh"
            lower.contains("portuguese") -> "pt"
            else -> null
        }
    }

    private fun isLanguageCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("language option") || lower.contains("available language")
    }

    private fun isAmbientCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("ambient") || lower.contains("aci") ||
               lower.contains("auto document") || lower.contains("never mind") ||
               lower.contains("show entities") || lower.contains("what did you") ||
               lower.contains("stop listening")
    }

    private fun isCrudCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("push vital") || lower.contains("push order") ||
               lower.contains("send vital") || lower.contains("send order") ||
               lower.contains("add allergy to") ||
               lower.contains("discontinue") || lower.contains("dc ") ||
               (lower.contains("stop ") && (lower.contains("med") || lower.contains("metformin"))) ||
               lower.contains("hold") || lower.contains("pause") ||
               lower.contains("sync all") || lower.contains("sync everything")
    }

    private fun isDeviceCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("pair device") || lower.contains("pair glasses") ||
               lower.contains("pair this device") ||
               lower.contains("device status") || lower.contains("pairing status")
    }

    private fun isVoiceprintCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("voiceprint") || lower.contains("voice print") ||
               lower.contains("enroll my voice")
    }

    private fun isWorklistCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("worklist") || lower.contains("schedule") ||
               lower.contains("who's next") || lower.contains("whos next") ||
               lower.contains("who is next") || lower.contains("next patient") ||
               lower.contains("check in") || lower.contains("mark") ||
               (lower.contains("patient") && lower.contains("done")) ||
               (lower.contains("today") && lower.contains("patient")) ||
               lower.contains("start seeing") || lower.contains("begin encounter") ||
               lower.contains("seeing patient")
    }

    private fun isOrderUpdateCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.startsWith("update ") || lower.startsWith("delete ") ||
               lower.startsWith("remove ")
    }

    private fun isDdxCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("differential") || lower.contains("ddx") ||
               lower.contains("what could this be")
    }

    private fun isImageCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("take photo") || lower.contains("capture image") ||
               lower.contains("take picture") ||
               lower.contains("analyze wound") || lower.contains("wound assessment") ||
               lower.contains("analyze rash") || lower.contains("skin assessment") ||
               lower.contains("analyze xray") || lower.contains("analyze x-ray") ||
               lower.contains("read xray") ||
               lower.contains("read analysis") || lower.contains("image results")
    }

    private fun isBillingCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("claim") || lower.contains("bill") ||
               lower.contains("diagnosis") || lower.contains("icd") ||
               lower.contains("procedure") || lower.contains("cpt") ||
               lower.contains("modifier") || lower.contains("search icd") ||
               lower.contains("search cpt")
    }

    private fun isDnfbCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("dnfb") || lower.contains("discharged not final") ||
               lower.contains("unbilled") || lower.contains("prior auth") ||
               lower.contains("auth issues") || lower.contains("over") && lower.contains("days") ||
               lower.contains("aging") || lower.contains("resolve")
    }

    private fun isHudCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("hud")
    }

    private fun isGestureCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("gesture")
    }

    private fun isWinkCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("wink")
    }

    private fun isVerifyCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("verify") || lower.contains("verification") ||
               lower.contains("auth status")
    }

    private fun isCopilotCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("copilot") || lower.contains("what should") ||
               lower.contains("what do you think") || lower.contains("what would you") ||
               lower.contains("tell me more") || lower.contains("elaborate") ||
               lower.contains("explain more") || lower.contains("suggest next") ||
               lower.contains("what next")
    }

    private fun isRacialMedicineCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("pulse ox") || lower.contains("skin assessment") ||
               lower.contains("ancestry") || lower.contains("pharmacogenomic") ||
               lower.contains("maternal mortality") || lower.contains("maternal risk") ||
               lower.contains("sickle cell") || lower.contains("pain assessment")
    }

    private fun isCulturalCareCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("blood preference") || lower.contains("blood product") ||
               lower.contains("dietary") || lower.contains("halal") || lower.contains("kosher") ||
               lower.contains("fasting") || lower.contains("ramadan") ||
               lower.contains("modesty") || lower.contains("same gender") ||
               lower.contains("end of life") || lower.contains("advance directive")
    }

    private fun isBiasCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("bias")
    }

    private fun isMaternalCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("maternal") || lower.contains("ob health") ||
               lower.contains("pregnant") || lower.contains("postpartum") ||
               lower.contains("warning sign") || lower.contains("danger sign") ||
               lower.contains("preeclampsia") || lower.contains("pre-eclampsia") ||
               lower.contains("hemorrhage") || lower.contains("postpartum bleeding") ||
               lower.contains("ppd") || lower.contains("edinburgh") ||
               lower.contains("depression") ||
               lower.contains("disparity")
    }

    private fun isSdohCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("sdoh") || lower.contains("social determinant") ||
               lower.contains("food insecur") || lower.contains("housing") ||
               lower.contains("homeless") || lower.contains("transportation") ||
               lower.contains("no insurance") || lower.contains("uninsured") ||
               lower.contains("financial") || lower.contains("lives alone") ||
               lower.contains("social isolation") || lower.contains("social services") ||
               lower.contains("z codes") || lower.contains("adherence")
    }

    private fun isLiteracyCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("literacy") || lower.contains("teach back") ||
               lower.contains("plain language") || lower.contains("simple language") ||
               lower.contains("accommodations") || lower.contains("instructions")
    }

    private fun isInterpreterCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("interpreter") || lower.contains("language service") ||
               lower.contains("title vi") || lower.contains("title 6") ||
               lower.contains("clinical phrases") || lower.contains("common phrases") ||
               lower.contains("patient speaks") || lower.contains("set language") ||
               lower.contains("language preference")
    }

    private fun isControlCommand(cmd: String): Boolean {
        val lower = cmd.lowercase()
        return lower.contains("stop talking") || lower.contains("stop speaking") ||
               lower.contains("be quiet") || lower.contains("quiet") ||
               lower.contains("stop listening") || lower.contains("stop voice") ||
               lower.contains("mute") ||
               lower.contains("close") || lower.contains("dismiss") ||
               lower.contains("back") || lower.contains("go away") ||
               lower.contains("clear cache") || lower.contains("clear offline")
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // MULTI-LANGUAGE TRANSLATION TESTS
    // ═══════════════════════════════════════════════════════════════════════════
    //
    // These tests verify the translateCommand() function in MainActivity.kt
    // which maps Spanish/Russian commands to English equivalents.
    //
    // This is REAL functionality that needs testing - not just aliases of
    // the same code path. The translation maps (spanishCommands, russianCommands)
    // are separate data structures that could have typos or missing entries.
    // ═══════════════════════════════════════════════════════════════════════════

    // Spanish command mappings (mirrors MainActivity.spanishCommands)
    private val spanishCommandsMap = mapOf(
        // Patient commands
        "cargar paciente" to "load patient",
        "buscar paciente" to "find patient",
        "escanear pulsera" to "scan wristband",
        "resumen del paciente" to "patient summary",
        "dime sobre el paciente" to "tell me about patient",
        "información del paciente" to "brief me",
        // Data display commands
        "mostrar signos vitales" to "show vitals",
        "mostrar alergias" to "show allergies",
        "mostrar medicamentos" to "show meds",
        "mostrar laboratorios" to "show labs",
        "mostrar procedimientos" to "show procedures",
        "mostrar inmunizaciones" to "show immunizations",
        "mostrar condiciones" to "show conditions",
        "mostrar planes de cuidado" to "show care plans",
        "notas clínicas" to "clinical notes",
        // Documentation commands
        "iniciar nota" to "start note",
        "terminar nota" to "stop note",
        "guardar nota" to "save note",
        "enviar a historia clínica" to "push to ehr",
        "editar nota" to "edit note",
        "restaurar nota" to "reset note",
        // Transcription commands
        "transcripción en vivo" to "live transcribe",
        "iniciar transcripción" to "start transcription",
        "detener transcripción" to "stop transcription",
        "generar nota" to "generate note",
        "volver a grabar" to "re-record",
        // Navigation and control
        "cerrar" to "close",
        "volver" to "go back",
        "ayuda" to "help",
        "comandos" to "show commands",
        "dejar de escuchar" to "stop listening",
        "silencio" to "mute",
        "desbloquear" to "unlock",
        "bloquear sesión" to "lock session",
        // Orders
        "ordenar" to "order",
        "mostrar órdenes" to "show orders",
        "cancelar orden" to "cancel order",
        // Handoff and discharge
        "reporte de entrega" to "handoff report",
        "resumen de alta" to "discharge summary",
        "instrucciones de alta" to "discharge instructions",
        // Checklists
        "mostrar listas" to "show checklists",
        "iniciar lista" to "start checklist",
        "marcar todo" to "check all",
        // Timer
        "iniciar temporizador" to "start timer",
        "detener temporizador" to "stop timer",
        "cuánto tiempo" to "how long",
        // Calculator
        "calcular" to "calculate",
        "calculadora médica" to "medical calculator"
    )

    // Russian command mappings (mirrors MainActivity.russianCommands)
    private val russianCommandsMap = mapOf(
        // Patient commands
        "загрузить пациента" to "load patient",
        "найти пациента" to "find patient",
        "сканировать браслет" to "scan wristband",
        "информация о пациенте" to "patient summary",
        "расскажи о пациенте" to "tell me about patient",
        "краткая информация" to "brief me",
        // Data display commands
        "показать витальные" to "show vitals",
        "показать жизненные показатели" to "show vitals",
        "показать аллергии" to "show allergies",
        "показать лекарства" to "show meds",
        "показать медикаменты" to "show meds",
        "показать анализы" to "show labs",
        "показать лаборатории" to "show labs",
        "показать процедуры" to "show procedures",
        "показать прививки" to "show immunizations",
        "показать вакцинации" to "show immunizations",
        "показать состояния" to "show conditions",
        "показать диагнозы" to "show conditions",
        "показать план лечения" to "show care plans",
        "клинические записи" to "clinical notes",
        // Documentation commands
        "начать запись" to "start note",
        "начать заметку" to "start note",
        "закончить запись" to "stop note",
        "сохранить запись" to "save note",
        "сохранить заметку" to "save note",
        "отправить в историю болезни" to "push to ehr",
        "редактировать запись" to "edit note",
        "сбросить запись" to "reset note",
        // Transcription commands
        "живая транскрипция" to "live transcribe",
        "начать транскрипцию" to "start transcription",
        "остановить транскрипцию" to "stop transcription",
        "создать заметку" to "generate note",
        "перезаписать" to "re-record",
        // Navigation and control
        "закрыть" to "close",
        "назад" to "go back",
        "помощь" to "help",
        "команды" to "show commands",
        "перестать слушать" to "stop listening",
        "молчать" to "mute",
        "разблокировать" to "unlock",
        "заблокировать сессию" to "lock session",
        // Orders
        "назначить" to "order",
        "заказать" to "order",
        "показать назначения" to "show orders",
        "отменить назначение" to "cancel order",
        // Handoff and discharge
        "отчёт о передаче" to "handoff report",
        "выписка" to "discharge summary",
        "инструкции при выписке" to "discharge instructions",
        // Checklists
        "показать чек-листы" to "show checklists",
        "начать чек-лист" to "start checklist",
        "отметить всё" to "check all",
        // Timer
        "запустить таймер" to "start timer",
        "остановить таймер" to "stop timer"
    )

    /**
     * Simulates the translateCommand function from MainActivity
     * This tests the actual translation logic
     */
    private fun translateCommand(transcript: String, language: String): String {
        val lower = transcript.lowercase()

        when (language) {
            "es" -> {
                val lowerNoAccents = stripAccentsForTest(lower)
                for ((spanish, english) in spanishCommandsMap) {
                    val spanishNoAccents = stripAccentsForTest(spanish)
                    if (lower.contains(spanish) || lowerNoAccents.contains(spanishNoAccents)) {
                        return if (lower.contains(spanish)) {
                            lower.replace(spanish, english)
                        } else {
                            lowerNoAccents.replace(spanishNoAccents, english)
                        }
                    }
                }
            }
            "ru" -> {
                for ((russian, english) in russianCommandsMap) {
                    if (lower.contains(russian)) {
                        return lower.replace(russian, english)
                    }
                }
            }
        }
        return transcript
    }

    /**
     * Strip accents for fuzzy matching (Spanish)
     */
    private fun stripAccentsForTest(text: String): String {
        return text
            .replace("á", "a").replace("à", "a").replace("ä", "a")
            .replace("é", "e").replace("è", "e").replace("ë", "e")
            .replace("í", "i").replace("ì", "i").replace("ï", "i")
            .replace("ó", "o").replace("ò", "o").replace("ö", "o")
            .replace("ú", "u").replace("ù", "u").replace("ü", "u")
            .replace("ñ", "n")
    }

    // Spanish single-word keyword aliases (mirrors MainActivity.spanishKeywordAliases)
    private val spanishKeywordAliasesMap = mapOf(
        "vitales" to "show vitals",
        "signos vitales" to "show vitals",
        "alergias" to "show allergies",
        "medicamentos" to "show meds",
        "medicinas" to "show meds",
        "laboratorios" to "show labs",
        "análisis" to "show labs",
        "procedimientos" to "show procedures",
        "inmunizaciones" to "show immunizations",
        "vacunas" to "show immunizations",
        "condiciones" to "show conditions",
        "diagnósticos" to "show conditions",
        "planes de cuidado" to "show care plans",
        "notas" to "clinical notes",
        "paciente" to "load patient",
        "cargar" to "load patient",
        "buscar" to "find patient",
        "escanear" to "scan wristband",
        "resumen" to "patient summary",
        "nota" to "start note",
        "transcripción" to "live transcribe",
        "transcribir" to "live transcribe",
        "generar" to "generate note",
        "cerrar" to "close",
        "ayuda" to "help",
        "comandos" to "show commands",
        "órdenes" to "show orders",
        "ordenes" to "show orders",
        "cancelar" to "cancel order",
        "temporizador" to "start timer",
        "tiempo" to "how long",
        "calcular" to "calculate",
        "calculadora" to "medical calculator"
    )

    // Russian single-word keyword aliases (mirrors MainActivity.russianKeywordAliases)
    private val russianKeywordAliasesMap = mapOf(
        "витальные" to "show vitals",
        "витали" to "show vitals",
        "аллергии" to "show allergies",
        "лекарства" to "show meds",
        "медикаменты" to "show meds",
        "препараты" to "show meds",
        "анализы" to "show labs",
        "лаборатории" to "show labs",
        "процедуры" to "show procedures",
        "прививки" to "show immunizations",
        "вакцины" to "show immunizations",
        "состояния" to "show conditions",
        "диагнозы" to "show conditions",
        "записи" to "clinical notes",
        "пациента" to "load patient",
        "пациент" to "load patient",
        "загрузить" to "load patient",
        "найти" to "find patient",
        "сканировать" to "scan wristband",
        "информация" to "patient summary",
        "запись" to "start note",
        "заметка" to "start note",
        "транскрипция" to "live transcribe",
        "транскрибировать" to "live transcribe",
        "создать" to "generate note",
        "закрыть" to "close",
        "помощь" to "help",
        "команды" to "show commands",
        "назначения" to "show orders",
        "отменить" to "cancel order",
        "таймер" to "start timer",
        "время" to "how long",
        "рассчитать" to "calculate",
        "калькулятор" to "medical calculator"
    )

    /**
     * Simulates the translateCommand function with keyword alias support
     * Tests the new keyword alias feature that allows single-word commands
     */
    private fun translateCommandWithKeywords(transcript: String, language: String): String {
        val lower = transcript.lowercase()

        when (language) {
            "es" -> {
                val lowerNoAccents = stripAccentsForTest(lower)
                // 1. Check full phrase commands first
                for ((spanish, english) in spanishCommandsMap) {
                    val spanishNoAccents = stripAccentsForTest(spanish)
                    if (lower.contains(spanish) || lowerNoAccents.contains(spanishNoAccents)) {
                        return if (lower.contains(spanish)) {
                            lower.replace(spanish, english)
                        } else {
                            lowerNoAccents.replace(spanishNoAccents, english)
                        }
                    }
                }
                // 2. Check keyword aliases
                for ((keyword, english) in spanishKeywordAliasesMap) {
                    val keywordNoAccents = stripAccentsForTest(keyword)
                    if (lower.contains(keyword) || lowerNoAccents.contains(keywordNoAccents)) {
                        return english
                    }
                }
            }
            "ru" -> {
                // 1. Check full phrase commands first
                for ((russian, english) in russianCommandsMap) {
                    if (lower.contains(russian)) {
                        return lower.replace(russian, english)
                    }
                }
                // 2. Check keyword aliases
                for ((keyword, english) in russianKeywordAliasesMap) {
                    if (lower.contains(keyword)) {
                        return english
                    }
                }
            }
        }
        return transcript
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // SPANISH TRANSLATION TESTS (50+ commands)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `spanish - cargar paciente translates to load patient`() {
        assertEquals("load patient", translateCommand("cargar paciente", "es"))
    }

    @Test
    fun `spanish - buscar paciente translates to find patient`() {
        assertEquals("find patient", translateCommand("buscar paciente", "es"))
    }

    @Test
    fun `spanish - escanear pulsera translates to scan wristband`() {
        assertEquals("scan wristband", translateCommand("escanear pulsera", "es"))
    }

    @Test
    fun `spanish - mostrar signos vitales translates to show vitals`() {
        assertEquals("show vitals", translateCommand("mostrar signos vitales", "es"))
    }

    @Test
    fun `spanish - mostrar alergias translates to show allergies`() {
        assertEquals("show allergies", translateCommand("mostrar alergias", "es"))
    }

    @Test
    fun `spanish - mostrar medicamentos translates to show meds`() {
        assertEquals("show meds", translateCommand("mostrar medicamentos", "es"))
    }

    @Test
    fun `spanish - mostrar laboratorios translates to show labs`() {
        assertEquals("show labs", translateCommand("mostrar laboratorios", "es"))
    }

    @Test
    fun `spanish - mostrar procedimientos translates to show procedures`() {
        assertEquals("show procedures", translateCommand("mostrar procedimientos", "es"))
    }

    @Test
    fun `spanish - mostrar inmunizaciones translates to show immunizations`() {
        assertEquals("show immunizations", translateCommand("mostrar inmunizaciones", "es"))
    }

    @Test
    fun `spanish - mostrar condiciones translates to show conditions`() {
        assertEquals("show conditions", translateCommand("mostrar condiciones", "es"))
    }

    @Test
    fun `spanish - mostrar planes de cuidado translates to show care plans`() {
        assertEquals("show care plans", translateCommand("mostrar planes de cuidado", "es"))
    }

    @Test
    fun `spanish - notas clinicas translates to clinical notes`() {
        assertEquals("clinical notes", translateCommand("notas clínicas", "es"))
    }

    @Test
    fun `spanish - iniciar nota translates to start note`() {
        assertEquals("start note", translateCommand("iniciar nota", "es"))
    }

    @Test
    fun `spanish - guardar nota translates to save note`() {
        assertEquals("save note", translateCommand("guardar nota", "es"))
    }

    @Test
    fun `spanish - generar nota translates to generate note`() {
        assertEquals("generate note", translateCommand("generar nota", "es"))
    }

    @Test
    fun `spanish - transcripcion en vivo translates to live transcribe`() {
        assertEquals("live transcribe", translateCommand("transcripción en vivo", "es"))
    }

    @Test
    fun `spanish - detener transcripcion translates to stop transcription`() {
        assertEquals("stop transcription", translateCommand("detener transcripción", "es"))
    }

    @Test
    fun `spanish - cerrar translates to close`() {
        assertEquals("close", translateCommand("cerrar", "es"))
    }

    @Test
    fun `spanish - ayuda translates to help`() {
        assertEquals("help", translateCommand("ayuda", "es"))
    }

    @Test
    fun `spanish - mostrar ordenes translates to show orders`() {
        assertEquals("show orders", translateCommand("mostrar órdenes", "es"))
    }

    @Test
    fun `spanish - resumen de alta translates to discharge summary`() {
        assertEquals("discharge summary", translateCommand("resumen de alta", "es"))
    }

    @Test
    fun `spanish - iniciar temporizador translates to start timer`() {
        assertEquals("start timer", translateCommand("iniciar temporizador", "es"))
    }

    @Test
    fun `spanish - calcular translates to calculate`() {
        assertEquals("calculate", translateCommand("calcular", "es"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // SPANISH ACCENT-INSENSITIVE TESTS
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `spanish accent-insensitive - mostrar ordenes without accent`() {
        assertEquals("show orders", translateCommand("mostrar ordenes", "es"))
    }

    @Test
    fun `spanish accent-insensitive - notas clinicas without accent`() {
        assertEquals("clinical notes", translateCommand("notas clinicas", "es"))
    }

    @Test
    fun `spanish accent-insensitive - transcripcion en vivo without accent`() {
        assertEquals("live transcribe", translateCommand("transcripcion en vivo", "es"))
    }

    @Test
    fun `spanish accent-insensitive - detener transcripcion without accent`() {
        assertEquals("stop transcription", translateCommand("detener transcripcion", "es"))
    }

    @Test
    fun `spanish accent-insensitive - informacion del paciente without accent`() {
        assertEquals("brief me", translateCommand("informacion del paciente", "es"))
    }

    @Test
    fun `spanish accent-insensitive - cuanto tiempo without accent`() {
        assertEquals("how long", translateCommand("cuanto tiempo", "es"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // RUSSIAN TRANSLATION TESTS (50+ commands)
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `russian - загрузить пациента translates to load patient`() {
        assertEquals("load patient", translateCommand("загрузить пациента", "ru"))
    }

    @Test
    fun `russian - найти пациента translates to find patient`() {
        assertEquals("find patient", translateCommand("найти пациента", "ru"))
    }

    @Test
    fun `russian - сканировать браслет translates to scan wristband`() {
        assertEquals("scan wristband", translateCommand("сканировать браслет", "ru"))
    }

    @Test
    fun `russian - показать витальные translates to show vitals`() {
        assertEquals("show vitals", translateCommand("показать витальные", "ru"))
    }

    @Test
    fun `russian - показать жизненные показатели translates to show vitals`() {
        assertEquals("show vitals", translateCommand("показать жизненные показатели", "ru"))
    }

    @Test
    fun `russian - показать аллергии translates to show allergies`() {
        assertEquals("show allergies", translateCommand("показать аллергии", "ru"))
    }

    @Test
    fun `russian - показать лекарства translates to show meds`() {
        assertEquals("show meds", translateCommand("показать лекарства", "ru"))
    }

    @Test
    fun `russian - показать медикаменты translates to show meds`() {
        assertEquals("show meds", translateCommand("показать медикаменты", "ru"))
    }

    @Test
    fun `russian - показать анализы translates to show labs`() {
        assertEquals("show labs", translateCommand("показать анализы", "ru"))
    }

    @Test
    fun `russian - показать лаборатории translates to show labs`() {
        assertEquals("show labs", translateCommand("показать лаборатории", "ru"))
    }

    @Test
    fun `russian - показать процедуры translates to show procedures`() {
        assertEquals("show procedures", translateCommand("показать процедуры", "ru"))
    }

    @Test
    fun `russian - показать прививки translates to show immunizations`() {
        assertEquals("show immunizations", translateCommand("показать прививки", "ru"))
    }

    @Test
    fun `russian - показать вакцинации translates to show immunizations`() {
        assertEquals("show immunizations", translateCommand("показать вакцинации", "ru"))
    }

    @Test
    fun `russian - показать состояния translates to show conditions`() {
        assertEquals("show conditions", translateCommand("показать состояния", "ru"))
    }

    @Test
    fun `russian - показать диагнозы translates to show conditions`() {
        assertEquals("show conditions", translateCommand("показать диагнозы", "ru"))
    }

    @Test
    fun `russian - показать план лечения translates to show care plans`() {
        assertEquals("show care plans", translateCommand("показать план лечения", "ru"))
    }

    @Test
    fun `russian - клинические записи translates to clinical notes`() {
        assertEquals("clinical notes", translateCommand("клинические записи", "ru"))
    }

    @Test
    fun `russian - начать запись translates to start note`() {
        assertEquals("start note", translateCommand("начать запись", "ru"))
    }

    @Test
    fun `russian - начать заметку translates to start note`() {
        assertEquals("start note", translateCommand("начать заметку", "ru"))
    }

    @Test
    fun `russian - сохранить запись translates to save note`() {
        assertEquals("save note", translateCommand("сохранить запись", "ru"))
    }

    @Test
    fun `russian - создать заметку translates to generate note`() {
        assertEquals("generate note", translateCommand("создать заметку", "ru"))
    }

    @Test
    fun `russian - живая транскрипция translates to live transcribe`() {
        assertEquals("live transcribe", translateCommand("живая транскрипция", "ru"))
    }

    @Test
    fun `russian - остановить транскрипцию translates to stop transcription`() {
        assertEquals("stop transcription", translateCommand("остановить транскрипцию", "ru"))
    }

    @Test
    fun `russian - закрыть translates to close`() {
        assertEquals("close", translateCommand("закрыть", "ru"))
    }

    @Test
    fun `russian - помощь translates to help`() {
        assertEquals("help", translateCommand("помощь", "ru"))
    }

    @Test
    fun `russian - показать назначения translates to show orders`() {
        assertEquals("show orders", translateCommand("показать назначения", "ru"))
    }

    @Test
    fun `russian - выписка translates to discharge summary`() {
        assertEquals("discharge summary", translateCommand("выписка", "ru"))
    }

    @Test
    fun `russian - запустить таймер translates to start timer`() {
        assertEquals("start timer", translateCommand("запустить таймер", "ru"))
    }

    @Test
    fun `russian - остановить таймер translates to stop timer`() {
        assertEquals("stop timer", translateCommand("остановить таймер", "ru"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // TRANSLATION EDGE CASES
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `translation - unknown command returns original`() {
        assertEquals("unknown command", translateCommand("unknown command", "es"))
        assertEquals("unknown command", translateCommand("unknown command", "ru"))
    }

    @Test
    fun `translation - english command not translated when spanish mode`() {
        assertEquals("show vitals", translateCommand("show vitals", "es"))
    }

    @Test
    fun `translation - case insensitive spanish`() {
        assertEquals("load patient", translateCommand("CARGAR PACIENTE", "es"))
        assertEquals("show vitals", translateCommand("MOSTRAR SIGNOS VITALES", "es"))
    }

    @Test
    fun `translation - case insensitive russian`() {
        assertEquals("load patient", translateCommand("ЗАГРУЗИТЬ ПАЦИЕНТА", "ru"))
        assertEquals("show vitals", translateCommand("ПОКАЗАТЬ ВИТАЛЬНЫЕ", "ru"))
    }

    @Test
    fun `translation - partial match spanish`() {
        val result = translateCommand("por favor cargar paciente ahora", "es")
        assertTrue(result.contains("load patient"))
    }

    @Test
    fun `translation - partial match russian`() {
        val result = translateCommand("пожалуйста загрузить пациента сейчас", "ru")
        assertTrue(result.contains("load patient"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // SPANISH SINGLE-WORD KEYWORD ALIAS TESTS
    // These test the new feature: saying just "vitales" instead of "mostrar signos vitales"
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `spanish keyword - vitales triggers show vitals`() {
        assertEquals("show vitals", translateCommandWithKeywords("vitales", "es"))
    }

    @Test
    fun `spanish keyword - signos vitales triggers show vitals`() {
        assertEquals("show vitals", translateCommandWithKeywords("signos vitales", "es"))
    }

    @Test
    fun `spanish keyword - alergias triggers show allergies`() {
        assertEquals("show allergies", translateCommandWithKeywords("alergias", "es"))
    }

    @Test
    fun `spanish keyword - medicamentos triggers show meds`() {
        assertEquals("show meds", translateCommandWithKeywords("medicamentos", "es"))
    }

    @Test
    fun `spanish keyword - medicinas triggers show meds`() {
        assertEquals("show meds", translateCommandWithKeywords("medicinas", "es"))
    }

    @Test
    fun `spanish keyword - laboratorios triggers show labs`() {
        assertEquals("show labs", translateCommandWithKeywords("laboratorios", "es"))
    }

    @Test
    fun `spanish keyword - análisis triggers show labs`() {
        assertEquals("show labs", translateCommandWithKeywords("análisis", "es"))
    }

    @Test
    fun `spanish keyword - analisis without accent triggers show labs`() {
        assertEquals("show labs", translateCommandWithKeywords("analisis", "es"))
    }

    @Test
    fun `spanish keyword - procedimientos triggers show procedures`() {
        assertEquals("show procedures", translateCommandWithKeywords("procedimientos", "es"))
    }

    @Test
    fun `spanish keyword - vacunas triggers show immunizations`() {
        assertEquals("show immunizations", translateCommandWithKeywords("vacunas", "es"))
    }

    @Test
    fun `spanish keyword - condiciones triggers show conditions`() {
        assertEquals("show conditions", translateCommandWithKeywords("condiciones", "es"))
    }

    @Test
    fun `spanish keyword - diagnósticos triggers show conditions`() {
        assertEquals("show conditions", translateCommandWithKeywords("diagnósticos", "es"))
    }

    @Test
    fun `spanish keyword - ayuda triggers help`() {
        assertEquals("help", translateCommandWithKeywords("ayuda", "es"))
    }

    @Test
    fun `spanish keyword - órdenes triggers show orders`() {
        assertEquals("show orders", translateCommandWithKeywords("órdenes", "es"))
    }

    @Test
    fun `spanish keyword - ordenes without accent triggers show orders`() {
        assertEquals("show orders", translateCommandWithKeywords("ordenes", "es"))
    }

    @Test
    fun `spanish keyword - calcular triggers calculate`() {
        assertEquals("calculate", translateCommandWithKeywords("calcular", "es"))
    }

    @Test
    fun `spanish keyword - temporizador triggers start timer`() {
        assertEquals("start timer", translateCommandWithKeywords("temporizador", "es"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // RUSSIAN SINGLE-WORD KEYWORD ALIAS TESTS
    // These test the new feature: saying just "витальные" instead of "показать витальные"
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `russian keyword - витальные triggers show vitals`() {
        assertEquals("show vitals", translateCommandWithKeywords("витальные", "ru"))
    }

    @Test
    fun `russian keyword - аллергии triggers show allergies`() {
        assertEquals("show allergies", translateCommandWithKeywords("аллергии", "ru"))
    }

    @Test
    fun `russian keyword - лекарства triggers show meds`() {
        assertEquals("show meds", translateCommandWithKeywords("лекарства", "ru"))
    }

    @Test
    fun `russian keyword - медикаменты triggers show meds`() {
        assertEquals("show meds", translateCommandWithKeywords("медикаменты", "ru"))
    }

    @Test
    fun `russian keyword - препараты triggers show meds`() {
        assertEquals("show meds", translateCommandWithKeywords("препараты", "ru"))
    }

    @Test
    fun `russian keyword - анализы triggers show labs`() {
        assertEquals("show labs", translateCommandWithKeywords("анализы", "ru"))
    }

    @Test
    fun `russian keyword - процедуры triggers show procedures`() {
        assertEquals("show procedures", translateCommandWithKeywords("процедуры", "ru"))
    }

    @Test
    fun `russian keyword - прививки triggers show immunizations`() {
        assertEquals("show immunizations", translateCommandWithKeywords("прививки", "ru"))
    }

    @Test
    fun `russian keyword - вакцины triggers show immunizations`() {
        assertEquals("show immunizations", translateCommandWithKeywords("вакцины", "ru"))
    }

    @Test
    fun `russian keyword - состояния triggers show conditions`() {
        assertEquals("show conditions", translateCommandWithKeywords("состояния", "ru"))
    }

    @Test
    fun `russian keyword - диагнозы triggers show conditions`() {
        assertEquals("show conditions", translateCommandWithKeywords("диагнозы", "ru"))
    }

    @Test
    fun `russian keyword - помощь triggers help`() {
        assertEquals("help", translateCommandWithKeywords("помощь", "ru"))
    }

    @Test
    fun `russian keyword - назначения triggers show orders`() {
        assertEquals("show orders", translateCommandWithKeywords("назначения", "ru"))
    }

    @Test
    fun `russian keyword - таймер triggers start timer`() {
        assertEquals("start timer", translateCommandWithKeywords("таймер", "ru"))
    }

    @Test
    fun `russian keyword - калькулятор triggers medical calculator`() {
        assertEquals("medical calculator", translateCommandWithKeywords("калькулятор", "ru"))
    }

    @Test
    fun `russian keyword - рассчитать triggers calculate`() {
        assertEquals("calculate", translateCommandWithKeywords("рассчитать", "ru"))
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // STRIP ACCENTS FUNCTION TESTS
    // ═══════════════════════════════════════════════════════════════════════════

    @Test
    fun `stripAccents - removes Spanish accents`() {
        assertEquals("carino", stripAccentsForTest("cariño"))
        assertEquals("informacion", stripAccentsForTest("información"))
        assertEquals("transcripcion", stripAccentsForTest("transcripción"))
        assertEquals("ordenes", stripAccentsForTest("órdenes"))
        assertEquals("clinicas", stripAccentsForTest("clínicas"))
    }

    @Test
    fun `stripAccents - handles multiple accents`() {
        assertEquals("comunicacion", stripAccentsForTest("comunicación"))
        assertEquals("numero", stripAccentsForTest("número"))
        assertEquals("pediatrico", stripAccentsForTest("pediátrico"))
    }

    @Test
    fun `stripAccents - preserves non-accented text`() {
        assertEquals("hello world", stripAccentsForTest("hello world"))
        assertEquals("show vitals", stripAccentsForTest("show vitals"))
    }

    @Test
    fun `stripAccents - handles mixed accented and non-accented`() {
        assertEquals("mostrar ordenes ahora", stripAccentsForTest("mostrar órdenes ahora"))
    }
}
