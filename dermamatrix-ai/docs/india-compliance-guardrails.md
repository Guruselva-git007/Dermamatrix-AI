# India compliance guardrails — college prototype

This implementation is a **compliance-oriented product prototype**, not a legal or regulatory certification. Legal counsel, clinical governance, security review, and applicable CDSCO assessment are required before any live launch.

## Product boundaries implemented

- The AI produces a screening-support result, never a verified diagnosis.
- Every result is explicitly marked **Awaiting RMP review**. A separate review-request record may be created, but it is not a diagnosis, counselling, or prescription.
- The product catalogue contains only generic cosmetic/personal-care categories. It does not recommend prescription medicines, doses, treatment regimens, brands, or paid rankings.
- Higher-risk screens block product discovery and point to clinician review.
- Profile and medical-history collection requires a clear, purpose-specific consent checkbox. The local database tracks profile, history, consent record, and review request separately.
- Image content is read in memory for the local assessment and is not saved by the prototype.

## Sources to validate before a production launch

- NMC rules and regulations: <https://www.nmc.org.in/rules-regulations-nmc/>
- NMC RMP conduct regulation archive (including telemedicine-platform provisions): <https://www.nmc.org.in/wp-content/uploads/2023/02/NMC_RMP_Conduct_Regulations_2023.pdf>
- CDSCO Drugs Rules, 1945: <https://cdsco.gov.in/opencms/opencms/en/Acts-and-rules/Drugs-Rules/>
- MeitY Digital Personal Data Protection Rules, 2025: <https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa>

## Required before real deployment

1. Contract and credential each RMP; validate registration against the NMR/State Medical Council before listing.
2. Add authenticated roles, encrypted storage, access logging, consent withdrawal/deletion, retention limits, breach response, and a privacy notice.
3. Use a licensed pharmacy partner, product registration/label checks, pharmacist review, adverse-event workflow, and no pay-to-rank results.
4. Validate models prospectively for each intended use, population and skin tone; assess CDSCO medical-device classification and obtain professional legal/regulatory advice.
