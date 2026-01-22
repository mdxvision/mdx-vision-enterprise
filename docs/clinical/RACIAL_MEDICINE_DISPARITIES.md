# Racial Disparities in Medicine: Research & Implementation Guide

## Executive Summary

Modern medicine has been built on a "white default" - research, diagnostic tools, clinical algorithms, and medical education have historically used Caucasian bodies as the standard. This creates measurable, documented harm to Black and Brown patients through misdiagnosis, delayed treatment, and inappropriate care protocols.

**This is not about cultural preferences. This is about clinical accuracy and patient safety.**

---

## 1. Pulse Oximeter Inaccuracy

### The Problem

Pulse oximeters - devices that measure blood oxygen levels - are less accurate on darker skin tones because melanin absorbs light that passes through the skin, interfering with readings.

### Research Findings

| Finding | Source |
|---------|--------|
| Black patients **3x more likely** to have dangerously low oxygen levels that pulse oximeters failed to detect | [University of Michigan Study](https://www.nejm.org/doi/full/10.1056/NEJMc2029240) |
| Oxygen levels overestimated by **1.7%** in Asian patients, **1.2%** in Black patients, **1.1%** in Hispanic patients vs. White patients | [Johns Hopkins](https://publichealth.jhu.edu/2024/pulse-oximeters-racial-bias) |
| Original pulse oximeters designed and tested in 1970s Japan with minimal skin tone variation | [Health Affairs](https://www.healthaffairs.org/do/10.1377/forefront.20250113.380292/) |

### Clinical Impact

- COVID-19 patients with darker skin may not have received therapies when they needed care due to falsely elevated SpO2 readings
- Missed hypoxia can lead to organ damage, delayed intubation, and death
- FDA issued draft guidance in January 2025 requiring manufacturers to test across diverse skin tones

### Implementation for MDx Vision

```
ALERT: SpO2 readings may be 1-4% higher than actual on darker skin tones.
Consider arterial blood gas (ABG) for critical decisions.
Patient skin tone: [Fitzpatrick IV-VI detected]
```

**Sources:**
- [Johns Hopkins - Pulse Oximeters' Racial Bias](https://publichealth.jhu.edu/2024/pulse-oximeters-racial-bias)
- [NEJM - Racial Bias in Pulse Oximetry](https://www.nejm.org/doi/full/10.1056/NEJMc2029240)
- [FDA Draft Guidance 2025](https://www.cnn.com/2025/01/06/health/fda-pulse-oximeters-draft-guidance)
- [AJMC - Racial and Ethnic Bias in Pulse Oximetry](https://www.ajmc.com/view/racial-and-ethnic-bias-in-pulse-oximetry-is-failing-patients)

---

## 2. Pharmacogenomics: Drug Response Differences

### The Problem

Many medications are metabolized differently based on genetic variations that correlate with ancestry. Treatment protocols developed primarily on White populations may be less effective or require different dosing for other populations.

### Key Medication Differences

| Medication Class | Finding | Source |
|-----------------|---------|--------|
| **ACE Inhibitors** | Reduced blood pressure response in Black patients; renin-angiotensin system less hyperactivated | [SAGE Journals](https://journals.sagepub.com/doi/10.1177/1060028018779082) |
| **Beta-Blockers** | VA Cooperative Trial showed Whites had better antihypertensive response; Blacks responded better to diuretics | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC2730023/) |
| **BiDil (isosorbide dinitrate/hydralazine)** | FDA-approved specifically for self-identified African Americans due to different responses to standard hypertension meds | [Nature Scitable](https://www.nature.com/scitable/topicpage/pharmacogenetics-personalized-medicine-and-race-744/) |
| **GRK5 Mutation** | Found in 40% of African Americans; provides heart failure protection similar to beta-blockers | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC2730023/) |

### Genetic Factors

- **ADRB1 gene variants** affect beta-blocker response
- **GRK5 gene variants** affect heart failure outcomes
- **Low plasma renin activity** common in patients of African ancestry
- **Higher salt sensitivity** in hypertension for African-descended populations

### Important Caveats

- Large overlap exists between racial groups in drug responses
- Genetic markers of ancestry more predictive than self-identified race
- Individual pharmacogenomic testing preferred over race-based assumptions

### Implementation for MDx Vision

```
CLINICAL CONSIDERATION: Patient ancestry may affect medication response.
- ACE inhibitors: Consider thiazide diuretic or CCB as first-line for African American patients with HTN
- Beta-blockers: May have reduced efficacy; monitor closely
- Consider pharmacogenomic testing for personalized dosing
```

**Sources:**
- [PMC - Ethnic Differences in Cardiovascular Drug Response](https://pmc.ncbi.nlm.nih.gov/articles/PMC2730023/)
- [SAGE - ACE Inhibitors and ARBs in Black Patients](https://journals.sagepub.com/doi/10.1177/1060028018779082)
- [PMC - Why African Ancestry Patients Respond Differently](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3681568/)

---

## 3. Dermatology Diagnostic Bias

### The Problem

Medical education uses predominantly light-skinned images, leaving physicians poorly trained to recognize conditions on darker skin. Skin conditions present differently on melanin-rich skin.

### Research Findings

| Finding | Source |
|---------|--------|
| Only **4.5%** of textbook images represent darker skin tones | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10706051/) |
| Only **1 in 10** medical training images are in black-brown Fitzpatrick range | [Stanford HAI](https://hai.stanford.edu/news/ai-shows-dermatology-educational-materials-often-lack-darker-skin-tones) |
| Ratio of light skin to skin of color images is **5:1** in dermatology resources | [STAT News](https://www.statnews.com/2020/07/21/dermatology-faces-reckoning-lack-of-darker-skin-in-textbooks-journals-harms-patients-of-color/) |
| Dermatologists lost **4 percentage points** accuracy on darker skin diagnoses | [MIT News](https://news.mit.edu/2024/doctors-more-difficulty-diagnosing-diseases-images-darker-skin-0205) |
| Physicians **2x more likely** to recommend biopsy for benign lesions and **less likely** for malignant ones in patients of color | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9743121/) |

### Clinical Presentation Differences

| Condition | Light Skin | Dark Skin |
|-----------|------------|-----------|
| **Cyanosis** | Blue lips/nail beds | Gray/white appearance |
| **Jaundice** | Yellow skin | Yellow sclera, palms, soles |
| **Erythema (redness)** | Pink/red | Purple/dark brown |
| **Pallor** | Pale/white | Grayish, ashen |
| **Rashes** | Red, clearly visible | Hyperpigmented, subtle |
| **Petechiae** | Red dots | Dark purple/brown dots |
| **Bruising** | Blue/purple | Darker, harder to see |

### High-Risk Conditions

- **Melanoma**: Often missed on dark skin; presents in atypical locations (palms, soles, nail beds)
- **Keloids**: More common in Black patients; affects surgical planning
- **Vitiligo**: Requires different examination techniques
- **Lupus erythematosus**: Different presentation patterns

### Implementation for MDx Vision

```
SKIN ASSESSMENT GUIDANCE: Patient has melanin-rich skin (Fitzpatrick IV-VI)
- Cyanosis: Check oral mucosa, conjunctiva (not just nail beds)
- Jaundice: Examine sclera, hard palate, palms
- Rashes: Look for texture changes, hyperpigmentation patterns
- Melanoma: Examine palms, soles, nail beds, mucous membranes
- Consider dermatology consult for uncertain presentations
```

**Sources:**
- [MIT News - Doctors Have Difficulty Diagnosing on Darker Skin](https://news.mit.edu/2024/doctors-more-difficulty-diagnosing-diseases-images-darker-skin-0205)
- [PMC - Skin Inclusion in Medical Education](https://pmc.ncbi.nlm.nih.gov/articles/PMC10706051/)
- [PMC - Racial Disparities in Dermatology](https://pmc.ncbi.nlm.nih.gov/articles/PMC9743121/)

---

## 4. Clinical Algorithm Bias

### The eGFR Race Correction Problem

For decades, the estimated glomerular filtration rate (eGFR) equation included a "race correction" that artificially increased kidney function estimates for Black patients by ~16%, based on unfounded assumptions about muscle mass.

### Impact

| Impact | Numbers | Source |
|--------|---------|--------|
| Black Americans who would cross CKD Stage 3 threshold without race correction | **3.3 million** | [Yale School of Medicine](https://medicine.yale.edu/news-article/abandoning-a-race-biased-tool-for-kidney-diagnosis/) |
| Additional patients who would qualify for nephrologist referral | **300,000** | [Yale School of Medicine](https://medicine.yale.edu/news-article/abandoning-a-race-biased-tool-for-kidney-diagnosis/) |
| Additional patients eligible for transplant evaluation | **31,000** | [Yale School of Medicine](https://medicine.yale.edu/news-article/abandoning-a-race-biased-tool-for-kidney-diagnosis/) |
| African Americans are **4x more likely** to develop kidney failure than White patients | [Stanford FSI](https://healthpolicy.fsi.stanford.edu/news/removing-race-adjustment-chronic-kidney-disease-care) |

### Official Position (2021)

The National Kidney Foundation and American Society of Nephrology now recommend **race-free eGFR equations** (CKD-EPI 2021).

### Other Algorithms with Race-Based Adjustments

- **VBAC (Vaginal Birth After Cesarean) Calculator**: Lower success rates assigned to Black/Hispanic women
- **Pulmonary Function Tests**: "Race correction" for lung capacity
- **Cardiac Risk Scores**: Some include race as a factor
- **Fracture Risk Assessment (FRAX)**: Adjusts by race/ethnicity

### Implementation for MDx Vision

```
CALCULATOR: eGFR
Using CKD-EPI 2021 (race-free equation)
Note: Race-based corrections are no longer recommended per NKF/ASN guidance.
Result: [calculated value]

If using legacy system with race adjustment:
WARNING: This calculator uses outdated race-based correction.
Consider recalculating with CKD-EPI 2021 equation.
```

**Sources:**
- [NEJM - Reconsidering Race Correction in Clinical Algorithms](https://www.nejm.org/doi/full/10.1056/NEJMms2004740)
- [National Kidney Foundation - Removing Race](https://www.kidney.org/press-room/removing-race-estimates-kidney-function)
- [PMC - The Case Against Race-Based GFR](https://pmc.ncbi.nlm.nih.gov/articles/PMC9495470/)

---

## 5. Pain Management Disparities

### The Problem

Black patients are systematically undertreated for pain due to false beliefs about biological differences and implicit bias.

### Research Findings

| Finding | Source |
|---------|--------|
| Black patients **less likely** to receive analgesics for fractures (57% vs 74%) | [PNAS](https://www.pnas.org/doi/10.1073/pnas.1516047113) |
| **40%** of medical students believed "Black people's skin is thicker than White people's" | [UVA Study](https://news.virginia.edu/content/study-links-disparities-pain-management-racial-bias) |
| **50%** of medical students/residents endorsed false beliefs about biological differences | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC4843483/) |
| Black children with appendicitis less likely to receive appropriate opioids for severe pain | [AAMC](https://www.aamc.org/news/how-we-fail-black-patients-pain) |
| Greatest disparities for back pain, migraine, and abdominal pain | [Journal of Pain](https://www.jpain.org/article/S1526-5900(09)00775-5/fulltext) |

### False Beliefs Still Held by Medical Professionals

- "Black people's nerve endings are less sensitive"
- "Black people's skin is thicker"
- "Black people's blood coagulates more quickly"
- "Black people have higher pain tolerance"

**These beliefs have NO scientific basis.**

### Implementation for MDx Vision

```
PAIN ASSESSMENT REMINDER:
- Use standardized pain scales consistently across all patients
- Document patient-reported pain levels without subjective interpretation
- Research shows racial bias affects pain treatment decisions
- False beliefs about biological differences lead to undertreatment
- Consider: Is my assessment being influenced by implicit bias?
```

**Sources:**
- [PNAS - Racial Bias in Pain Assessment](https://www.pnas.org/doi/10.1073/pnas.1516047113)
- [JAMA Network - Racial Bias in Pain Treatment](https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2793179)
- [AAMC - How We Fail Black Patients in Pain](https://www.aamc.org/news/how-we-fail-black-patients-pain)

---

## 6. Maternal Mortality Crisis

### The Problem

Black women die from pregnancy-related causes at rates 3-4x higher than White women, regardless of income or education level.

### Statistics

| Metric | Value | Source |
|--------|-------|--------|
| Black maternal mortality rate | **49.4-55.3 per 100,000** | [KFF](https://www.kff.org/racial-equity-and-health-policy/issue-brief/racial-disparities-in-maternal-and-infant-health-current-status-and-efforts-to-address-them/) |
| White maternal mortality rate | **14.5-14.9 per 100,000** | [KFF](https://www.kff.org/racial-equity-and-health-policy/issue-brief/racial-disparities-in-maternal-and-infant-health-current-status-and-efforts-to-address-them/) |
| Disparity ratio | **3-4x higher** for Black women | [Johns Hopkins](https://publichealth.jhu.edu/2023/solving-the-black-maternal-health-crisis) |
| Discrimination contributed to pregnancy-related deaths (2020) | **30%** | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9914526/) |

### Key Finding

**High-income Black women have the same mortality risk as the poorest White women.** Education and income do not protect Black women from maternal mortality disparities.

### Contributing Factors

- Implicit bias in providers (84% acknowledge disparities exist, only 29% believe their own biases affect care)
- Black patients receive care at hospitals with higher mortality rates
- Dismissal of symptoms and concerns
- Delayed recognition of complications
- Historical medical mistrust

### Implementation for MDx Vision

```
OBSTETRIC ALERT: Patient at elevated risk for maternal complications
- Black women face 3-4x higher maternal mortality rates
- Listen to and document all patient-reported symptoms
- Lower threshold for escalation and specialist consultation
- Monitor closely for: preeclampsia, hemorrhage, cardiomyopathy, infection
- Document all concerns raised by patient, even if initially reassured
```

**Sources:**
- [KFF - Racial Disparities in Maternal Health](https://www.kff.org/racial-equity-and-health-policy/issue-brief/racial-disparities-in-maternal-and-infant-health-current-status-and-efforts-to-address-them/)
- [Johns Hopkins - Solving the Black Maternal Health Crisis](https://publichealth.jhu.edu/2023/solving-the-black-maternal-health-crisis)
- [PMC - Listen to the Whispers](https://pmc.ncbi.nlm.nih.gov/articles/PMC9914526/)

---

## 7. Sickle Cell Disease Treatment Disparities

### The Problem

Patients with sickle cell disease (predominantly Black patients) face stigma, longer wait times, and undertreatment in emergency departments.

### Research Findings

| Finding | Source |
|---------|--------|
| SCD patients labeled as "drug seekers" and "overutilizers" | [NC Medical Journal](https://ncmedicaljournal.com/article/91433-emergency-medicine-bias-in-treating-minorities-with-sickle-cell-disease) |
| SCD patients wait **16+ minutes longer** than general population | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3076949/) |
| 85% of providers cite concern about "drug-seeking behavior" | [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0006497125089025) |
| 90% uncomfortable with high-dose opioid prescribing | [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0006497125089025) |
| Some patients escorted out by police while in medical crisis | [Hematology.org](https://www.hematology.org/education/trainees/fellows/hematopoiesis/2022/emergency-department-management-of-sickle-cell-disease) |

### Clinical Reality

- Vaso-occlusive crisis causes **severe, objective pain**
- Pain is not drug-seeking behavior - it's a medical emergency
- Delays increase organ damage and stroke risk
- Patients often avoid ED due to past mistreatment

### Best Practice

**Adequate opioid therapy within 60 minutes of ED arrival** is the standard of care for vaso-occlusive pain episodes.

### Implementation for MDx Vision

```
SICKLE CELL CRISIS PROTOCOL:
- Target: Pain medication within 60 minutes of arrival
- Use patient's individualized pain plan if available
- Vaso-occlusive crisis is a MEDICAL EMERGENCY
- Do not delay treatment due to concerns about drug-seeking
- High-dose opioids are often medically necessary
- Monitor for complications: stroke, acute chest syndrome, splenic sequestration
```

**Sources:**
- [NC Medical Journal - Emergency Medicine Bias in SCD](https://ncmedicaljournal.com/article/91433-emergency-medicine-bias-in-treating-minorities-with-sickle-cell-disease)
- [ASH - Managing SCD Pain Crisis](https://ashpublications.org/blood/article/134/Supplement_1/2169/428032/Managing-Sickle-Cell-Disease-Patients-with-Acute)
- [PMC - Evaluation and Treatment of Sickle Cell Pain](https://pmc.ncbi.nlm.nih.gov/articles/PMC3076949/)

---

## 8. AI and Algorithm Bias

### The Problem

AI systems trained on biased data perpetuate and amplify existing disparities.

### Examples

| System | Bias | Impact |
|--------|------|--------|
| Dermatology AI | Trained predominantly on light skin | Misses melanoma on dark skin |
| Pulse oximeter algorithms | Calibrated on light skin | Overestimates O2 on dark skin |
| EHR-based algorithms | Reflect historical underdiagnosis | Perpetuate disparities |
| Risk prediction algorithms | Use healthcare costs as proxy for health needs | Underestimate needs of Black patients who historically received less care |

### Ruha Benjamin's "New Jim Code"

"Seemingly progressive technologies can reinforce racial hierarchies" - algorithms trained on historical data inherit biases from past discrimination.

### Implementation Principle

**AI should be a tool to REDUCE disparities, not perpetuate them.**

---

## Implementation Recommendations for MDx Vision

### 1. Patient Profile Enhancements

```kotlin
data class PatientDemographics(
    val selfIdentifiedRace: String?,
    val selfIdentifiedEthnicity: String?,
    val fitzpatrickSkinType: Int?,  // I-VI scale
    val relevantAncestry: List<String>?,  // For pharmacogenomics
    val geneticTestingResults: PharmacogenomicProfile?
)
```

### 2. Clinical Decision Support Alerts

| Trigger | Alert |
|---------|-------|
| SpO2 reading + darker skin tone | Pulse oximeter accuracy warning |
| HTN + African ancestry | Consider first-line medication alternatives |
| Skin assessment + darker skin | Modified assessment guidance |
| eGFR calculation | Use race-free CKD-EPI 2021 |
| Pain assessment | Implicit bias awareness prompt |
| Obstetric patient + Black race | Elevated risk monitoring |
| Sickle cell + ED visit | Rapid treatment protocol |

### 3. Voice Commands

| Command | Action |
|---------|--------|
| "skin assessment guidance" | Display melanin-specific exam tips |
| "medication considerations" | Show ancestry-relevant drug info |
| "check calculator bias" | Verify race-free algorithms used |
| "pain protocol" | Display bias-aware pain assessment |
| "sickle cell protocol" | Display rapid treatment protocol |

### 4. Audit and Monitoring

- Track treatment times by patient demographics
- Monitor pain medication prescribing patterns
- Flag potential diagnostic delays
- Report algorithm bias metrics

---

## References

### Pulse Oximetry
1. [Johns Hopkins - Pulse Oximeters' Racial Bias](https://publichealth.jhu.edu/2024/pulse-oximeters-racial-bias)
2. [NEJM - Racial Bias in Pulse Oximetry Measurement](https://www.nejm.org/doi/full/10.1056/NEJMc2029240)
3. [Health Affairs - The Overdue Imperative of Cross-Racial Pulse Oximeters](https://www.healthaffairs.org/do/10.1377/forefront.20250113.380292/)
4. [FDA Draft Guidance 2025](https://www.cnn.com/2025/01/06/health/fda-pulse-oximeters-draft-guidance)

### Pharmacogenomics
5. [Nature Scitable - Pharmacogenetics and Race](https://www.nature.com/scitable/topicpage/pharmacogenetics-personalized-medicine-and-race-744/)
6. [PMC - Ethnic Differences in Cardiovascular Drug Response](https://pmc.ncbi.nlm.nih.gov/articles/PMC2730023/)
7. [SAGE - ACE Inhibitors and ARBs in Black Patients](https://journals.sagepub.com/doi/10.1177/1060028018779082)

### Dermatology
8. [MIT News - Doctors Have Difficulty Diagnosing on Darker Skin](https://news.mit.edu/2024/doctors-more-difficulty-diagnosing-diseases-images-darker-skin-0205)
9. [PMC - Skin Inclusion in Medical Education](https://pmc.ncbi.nlm.nih.gov/articles/PMC10706051/)
10. [Stanford HAI - Dermatology Educational Materials Lack Darker Skin](https://hai.stanford.edu/news/ai-shows-dermatology-educational-materials-often-lack-darker-skin-tones)

### Clinical Algorithms
11. [NEJM - Reconsidering Race Correction in Clinical Algorithms](https://www.nejm.org/doi/full/10.1056/NEJMms2004740)
12. [National Kidney Foundation - Removing Race from eGFR](https://www.kidney.org/press-room/removing-race-estimates-kidney-function)
13. [Yale - Abandoning Race-Biased Kidney Diagnosis](https://medicine.yale.edu/news-article/abandoning-a-race-biased-tool-for-kidney-diagnosis/)

### Pain Management
14. [PNAS - Racial Bias in Pain Assessment](https://www.pnas.org/doi/10.1073/pnas.1516047113)
15. [JAMA Network - Racial Bias in Pain Treatment](https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2793179)
16. [AAMC - How We Fail Black Patients in Pain](https://www.aamc.org/news/how-we-fail-black-patients-pain)

### Maternal Mortality
17. [KFF - Racial Disparities in Maternal Health](https://www.kff.org/racial-equity-and-health-policy/issue-brief/racial-disparities-in-maternal-and-infant-health-current-status-and-efforts-to-address-them/)
18. [Johns Hopkins - Solving the Black Maternal Health Crisis](https://publichealth.jhu.edu/2023/solving-the-black-maternal-health-crisis)
19. [PMC - Listen to the Whispers](https://pmc.ncbi.nlm.nih.gov/articles/PMC9914526/)

### Sickle Cell Disease
20. [NC Medical Journal - Emergency Medicine Bias in SCD](https://ncmedicaljournal.com/article/91433-emergency-medicine-bias-in-treating-minorities-with-sickle-cell-disease)
21. [ASH - Managing SCD Pain Crisis](https://ashpublications.org/blood/article/134/Supplement_1/2169/428032/Managing-Sickle-Cell-Disease-Patients-with-Acute)
22. [Hematology.org - ED Management of SCD](https://www.hematology.org/education/trainees/fellows/hematopoiesis/2022/emergency-department-management-of-sickle-cell-disease)

---

*Last updated: Feature #79 Research - Racial Medicine Awareness*
