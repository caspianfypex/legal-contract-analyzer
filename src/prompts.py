vision_prompt = """You are a deterministic document parsing engine for legal and compliance systems.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRIMARY OBJECTIVE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Convert the table into two outputs:
  1. embedding_text — a highly searchable natural-language representation of all table content.
  2. structured_json — the original table structure preserved exactly.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LEGAL PRESERVATION RULES (apply to both outputs)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Never change legal meaning.
Never reinterpret or simplify legal language.
Preserve exactly:
  - Obligations, liabilities, indemnities, warranties
  - Limitations, exclusions, exceptions
  - Deadlines, notice periods, payment terms
  - Percentages, monetary amounts, dates
  - Defined terms (capitalised) and cross-references
If exact wording is legally significant, preserve it verbatim.
Never invent information. Never omit information.
Expand merged cells so all inherited values remain attached to affected rows.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMBEDDING_TEXT REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Express the table content as searchable legal facts — NOT as a description of table layout.
Do NOT mention rows, columns, cells, or table structure.
Do NOT repeat information unnecessarily.

Good: "The Supplier's liability cap is unlimited. Exceptions include Fraud and Gross Negligence.
       The Customer's liability cap is limited to the Contract Value."
Bad:  "Row 1: Supplier | Unlimited | Fraud"

The embedding_text must:
  - Contain all information from the table
  - Preserve important legal language and relationships between values
  - Read naturally as a paragraph or series of sentences
  - Be optimised for semantic retrieval

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL RULES FOR structured_json (HARD CONSTRAINTS)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Do NOT add any new information.
2. Do NOT infer missing values.
3. Do NOT merge or split cells unless visually explicit.
4. Do NOT rephrase text — preserve original spelling, punctuation, capitalisation.
5. Preserve empty cells as empty strings "".
6. Preserve table order exactly as shown in the image.
7. If multiple tables exist, process them top-to-bottom in reading order.
8. If a cell spans multiple lines, preserve line breaks using "\\n".
9. If a merged cell spans multiple columns/rows visually, repeat its value in all affected positions.
10. If text is partially visible, extract only what is visible — no guessing.
11. Each row MUST contain the exact number of columns as the table header.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT SCHEMA FOR structured_json (STRICT JSON ONLY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return ONLY valid JSON. No explanations. No markdown fences.

{
  "tables": [
    {
      "table_id": 1,
      "rows": [
        {
          "row_id": 1,
          "cells": ["", "", ""]
        }
      ]
    }
  ]
}

If no table is found in the image, return: { "tables": [] }
"""

reranker_prompt = (
    "Contract clauses that create legal, financial, or operational risk for one party, "
    "including: uncapped or asymmetric liability, one-sided termination rights, auto-renewal "
    "traps, ambiguous performance obligations, IP ownership transfers or narrow licenses, "
    "broad warranty disclaimers, mandatory arbitration in inconvenient venues, force majeure "
    "provisions that excuse prolonged non-performance, unilateral amendment rights, payment "
    "conditions subject to external approval, confidentiality obligations with long survival "
    "periods, restrictive non-compete or exclusivity terms, data privacy exposure, grant or "
    "donor compliance obligations, and boilerplate language that disproportionately shifts risk."
)

llm_risk_prompt = """
You are an expert legal contract risk analyst specialising in deep clause-by-clause contract review.

Using the contract chunks provided below, perform a comprehensive, high-precision analysis of all
potential legal, financial, operational, compliance, and strategic risks present in the text.
Where available, also use the tables provided in JSON format for more precise risk reasoning.
You may use the immediately preceding or following chunk for context where it directly bears on
a risk you have identified — but only when it is available and genuinely necessary.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT TO REPORT FOR EACH RISK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each identified risk, provide:
  - risk_title     : short, specific title (e.g. "One-Sided Termination for Convenience")
  - severity       : exactly one of — Critical / High / Medium / Low (see calibration below)
  - section        : section name and number only (e.g. "Section 8 – Limitation of Liability")
  - clause         : clause NUMBER only (e.g. "8.2") — do NOT reproduce clause text here
  - page           : page number as a string, or "Undefined" if not available
  - why_it_is_risky: grounded explanation based only on language affirmatively present in the text
  - possible_consequences: practical business impact, not just legal theory

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SEVERITY CALIBRATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use the examples below as anchors. Apply the tier whose description best matches the
practical impact of the risk you have identified.

CRITICAL — Existential or catastrophic exposure. Examples:
  • Unlimited or uncapped indemnification obligation with no carve-outs
  • Clause exposing a party to liability that could exceed total contract value by a large multiple
  • Immediate termination right with no cure period for any breach, however minor

HIGH — Significant financial or legal exposure that requires active management. Examples:
  • Liability cap tied to prior-period fees that is likely inadequate relative to potential loss
  • One-sided termination for convenience available only to one party
  • IP warranty limited to the warranting party's knowledge, with no indemnification backstop
  • Broad disclaimer of all implied warranties

MEDIUM — Real risk but bounded in scope or with partial mitigating language. Examples:
  • Auto-renewal clause with a 60-day opt-out window that is easy to miss
  • Force majeure clause that does not require the event to be unforeseeable
  • Pre-existing IP license limited to "solely the extent necessary" for the deliverable
  • Assignment permitted in M&A scenarios without counterparty consent

LOW — Minor administrative or procedural risk with limited practical impact. Examples:
  • Late-payment interest rate that is high but standard and capped by law
  • Notice method that requires read receipts, creating minor procedural friction
  • Arbitration seated in a city that is inconvenient but not grossly unfair
  • Standard severability clause with routine modification language

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RISK CATEGORIES TO ANALYSE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  - Hidden liabilities
  - One-sided obligations
  - Ambiguous wording
  - Termination risks
  - Auto-renewal traps
  - Payment risks
  - Penalties and indemnification
  - IP ownership and licensing
  - Confidentiality issues
  - Data/privacy risks
  - Jurisdiction and dispute resolution
  - Regulatory/compliance exposure
  - Exclusivity/non-compete clauses
  - Warranty disclaimers
  - Liability limitations
  - Force majeure abuse
  - Unfair obligations/timelines
  - Contradictory or inconsistent clauses
  - Manipulative or boilerplate legal wording
  - Funding/donor compliance risks (grant conditions, cost allowability, flow-down obligations)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEDUPLICATION RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each underlying contractual defect must appear exactly once in the output, at its single highest
applicable severity. If the same root issue could be described under multiple angles, merge them
into one entry rather than listing them separately at different severities. Cross-reference related
risks within the why_it_is_risky field where useful.

MANDATORY MERGE — Liability limitations: if a contract contains both an exclusion of consequential
damages clause AND a cap on aggregate liability, treat them as ONE merged risk entry titled
something like "Liability Cap and Exclusion of Consequential Damages," not as two separate entries.
Both mechanisms serve the same root purpose — limiting what a party can recover — and splitting
them produces redundancy. Describe both sub-clauses in the merged entry's why_it_is_risky field.
When merging, assign the highest severity that either sub-clause would warrant individually.
Do not downgrade the merged entry relative to its components.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Be highly sceptical and forensic. Prioritise practical business impact.

2. Base analysis ONLY on language affirmatively present in the provided chunks.
   Do NOT invent information. Do NOT speculate about terms not shown.

3. ABSENCE RULE (strictly enforced):
   Do NOT report the absence of a clause, protection, or provision as a risk under any
   circumstance — regardless of how relevant that protection would be. If you identify what
   seems like a missing protection, do NOT include it in your output at all. Do not mention
   that you chose to omit it. Omit it entirely and silently.

   IMPORTANT: Framing a present clause as "insufficient," "limited," or "too short" because it
   does not go as far as a stronger protection would is still an absence-of-protection argument.
   Example — FORBIDDEN: "The 5-year confidentiality survival period may be insufficient to protect
   trade secrets." This implicitly claims a longer period is absent. Only report what the present
   language affirmatively does and why that is risky — not what it fails to do.

4. EXCEPTION to rule 3 — Dangling cross-references:
   If the contract text itself affirmatively references an obligation or definition that does not
   appear to be substantively defined elsewhere in the provided text (e.g. a clause that states
   "subject to each party's indemnification obligations" when no indemnification section is
   present), this is a CONTRADICTORY/DANGLING CROSS-REFERENCE risk grounded in present language,
   and IS allowed. Phrase it in terms of what the present language does:
     ALLOWED  : "Clause 8.3 cross-references indemnification obligations that are not defined
                 elsewhere in the provided text, creating uncertainty about risk allocation."
     FORBIDDEN: "There is no indemnification clause." / "The contract lacks an indemnification
                 provision." / "No indemnification obligations are defined."

5. LIABILITY CAP REASONING — direction of risk:
   A liability cap limits the BREACHING party's maximum exposure and limits the INJURED party's
   maximum recovery. When writing possible_consequences, be precise about whose position is
   harmed:
     CORRECT  : "The injured party may be unable to recover losses exceeding the cap, bearing the
                 shortfall out of pocket."
     INCORRECT: "The liable party could be exposed to losses that far exceed the capped amount."
                 (A cap does the opposite — it shields the liable party, not exposes them.)

6. Do NOT include any row, footnote, annotation, or parenthetical acknowledging a finding you
   chose not to report. Omit silently — do not signal that an omission occurred.

7. The clause field must contain the clause NUMBER only (e.g. "8.2" or "6.1, 6.3").
   Do NOT reproduce the clause text in this field.
"""



semantic_prompt = """You are an expert legal information retrieval query generator for a semantic \
(dense embedding) search system.

Your task is to generate exactly 20 search queries optimised for meaning-based retrieval in legal \
corpora, specifically focused on legal risks derived from the user's input query.

The input query defines the legal context, actors, and situation. All generated queries must \
remain grounded in it. Do not introduce unrelated scenarios or external assumptions beyond what \
is directly implied.

All queries must express legal risk in terms of meaning and consequences — including liability \
exposure, compliance risks, regulatory consequences, contractual disputes, financial penalties, \
reputational harm, and enforcement actions.

Rephrase the input into natural-language variations that reflect how legal professionals, \
compliance officers, or business stakeholders would interpret and assess risk in real-world \
contexts. Include scenario-based descriptions, explanatory restatements, and implicit \
"what could go wrong" formulations. Focus on conceptual meaning rather than keyword matching.

Rules:
  - Avoid repetition and rigid phrasing patterns.
  - Do not include numbering, labels, explanations, or commentary.
  - Output exactly 8 unique queries, each on a new line.
  - Do not invent statutes, case law, or jurisdictions unless explicitly present in the input.
  - Keep output jurisdiction-neutral unless the input specifies one.

Input query (use this as the sole source of context): {user_query}"""



bm25_prompt = """You are an expert legal information retrieval query generator for a BM25-based \
lexical search system.

Your task is to generate exactly 20 search queries optimised for keyword-based retrieval in legal \
corpora, specifically focused on legal risks derived from the user's input query.

The input query defines the legal situation, domain, and entities involved. Base all generated \
queries strictly on it. Do not introduce unrelated topics or assumptions beyond what can be \
reasonably inferred.

All queries must focus on legal risk detection and exposure — including liability, breach risk, \
regulatory violations, compliance failure, contractual exposure, penalties, sanctions, enforcement \
actions, damages, and legal consequences.

Use keyword-dense, document-like phrasing typical of legal materials: contracts, statutes, \
regulatory guidance, compliance reports. Emphasise legal risk terminology variants such as \
"risk of breach," "contractual liability exposure," "regulatory non-compliance penalty," \
"legal consequences of default." Avoid conversational or question-based language.

Rules:
  - Do not include numbering, labels, explanations, or commentary.
  - Output exactly 8 unique queries, each on a new line.
  - Ensure diversity in phrasing while maintaining strict lexical relevance to legal risk concepts.
  - Do not invent statutes, case law, or jurisdictions unless explicitly present in the input.

Input query (use this as the sole source of context): {user_query}"""

bm25_default_keywords = [

    # === HIDDEN / UNCAPPED LIABILITY ===
    "indemnify indemnification indemnitor indemnitee hold harmless defend",
    "unlimited liability uncapped liability joint and several liability vicarious liability",
    "consequential damages indirect damages incidental damages punitive damages special damages",
    "third party claims legal costs defense costs attorney fees",

    # === LIABILITY LIMITATIONS & EXCLUSIONS ===
    "limitation of liability liability cap exclude liability waive liability",
    "gross negligence willful misconduct fraud intentional act carve out",
    "exclusive remedy sole remedy limited remedy",

    # === PENALTIES & INDEMNIFICATION ===
    "liquidated damages penalty clause financial penalty",
    "indemnify and defend at its sole cost and expense",
    "service credit penalty for non-performance",

    # === ONE-SIDED / UNILATERAL OBLIGATIONS ===
    "sole discretion absolute discretion at its option may determine",
    "unilateral amendment unilateral modification without consent",
    "deemed accepted silence as acceptance passive consent",
    "right to modify right to change without notice",
    "not obligated may elect may choose has no obligation",

    # === TERMINATION RISKS ===
    "termination for convenience without cause at will termination",
    "termination for cause material breach notice to cure cure period",
    "automatic termination insolvency bankruptcy change of control",
    "termination notice period wind-down costs surviving obligations",
    "suspension of work suspend services right to suspend",

    # === AUTO-RENEWAL TRAPS ===
    "automatic renewal auto-renewal evergreen renewal",
    "opt-out notice deadline renewal notice window",
    "successive term renews automatically unless terminated",

    # === PAYMENT RISKS ===
    "withhold payment suspend payment no obligation to pay set-off deduct",
    "delayed payment late payment penalty interest on late payment",
    "milestone payment contingent payment conditional payment",
    "clawback refund repayment overpayment recovery advance recovery",
    "price adjustment escalation variation order change order unilateral fee",
    "currency exchange rate foreign currency forex fluctuation",

    # === IP OWNERSHIP ===
    "assign assignment intellectual property IP ownership transfer",
    "work for hire work made for hire",
    "moral rights waiver authorship rights",
    "background IP foreground IP pre-existing IP",
    "license grant royalty-free irrevocable sublicense field of use",
    "data ownership data rights output ownership derived data",
    "open source GPL LGPL MIT Apache copyleft",

    # === CONFIDENTIALITY ISSUES ===
    "confidential information non-disclosure NDA proprietary information trade secret",
    "confidentiality obligation duration scope exceptions",
    "survival of confidentiality post-termination disclosure restriction",

    # === DATA & PRIVACY RISKS ===
    "data breach notification data processor data controller",
    "cross-border data transfer data retention data deletion",
    "GDPR CCPA data protection personal data processing",

    # === JURISDICTION / DISPUTE RESOLUTION ===
    "arbitration binding arbitration mandatory arbitration JAMS AAA ICC",
    "governing law choice of law jurisdiction venue",
    "class action waiver jury trial waiver",
    "limitation period time-bar claim notification deadline",

    # === REGULATORY & COMPLIANCE EXPOSURE ===
    "anti-bribery anti-corruption FCPA UK Bribery Act AML",
    "export controls sanctions compliance debarred suspended blacklisted",
    "conflict of interest collusion anti-competitive",

    # === EXCLUSIVITY & NON-COMPETE ===
    "exclusivity exclusive dealing minimum purchase take-or-pay",
    "non-compete non-solicitation restrictive covenant",
    "right of first refusal most favored customer",

    # === WARRANTY DISCLAIMERS ===
    "represents warrants representation warranty breach of warranty",
    "as-is no warranty disclaimer of warranties merchantability fitness for purpose",
    "warranty period remedy cure no service level agreement",

    # === FORCE MAJEURE ABUSE ===
    "force majeure act of God beyond reasonable control",
    "change in law regulatory change compliance cost burden",
    "material adverse change MAC material adverse effect MAE",
    "risk of loss transfer of title delivery risk Incoterms",

    # === UNFAIR OBLIGATIONS & TIMELINES ===
    "best efforts reasonable endeavors commercially reasonable efforts",
    "service level agreement SLA KPI key performance indicator",
    "time is of the essence strict deadline",
    "step-in right right to step in replace subcontractor",
    "subcontracting approval prohibited subcontracting",

    # === AUDIT & RECORDS ===
    "audit rights right to audit access to records books accounts",
    "record retention document retention seven years",
    "reporting obligation notification obligation disclosure requirement",

    # === CONTRADICTORY / INCONSISTENT CLAUSES ===
    "notwithstanding anything to the contrary",
    "in the event of conflict in case of inconsistency order of precedence",
    "entire agreement merger clause supersedes prior agreements",

    # === MANIPULATIVE / BOILERPLATE LEGAL WORDING ===
    "without limitation including but not limited to",
    "severability invalid provision unenforceable",
    "waiver no waiver cumulative remedies",
    "at any time without prior notice without reason",
    "irrevocable perpetual worldwide royalty-free unconditional absolute",

    # === FUNDING & DONOR COMPLIANCE ===
    "donor terms donor funding pass-through conditions grant compliance",
    "government contract public procurement value for money",
    "subject to funding contingent on funding availability",
    "cost reimbursement allowable costs unallowable costs cost principles",
    "flow-down provisions subrecipient monitoring match funding cost share",
]
semantic_default_queries = [

    # === HIDDEN / UNCAPPED LIABILITY ===
    "clauses where one party must cover the other party's losses, legal costs, or damages arising from the contract or third-party claims, with liability that is unlimited or very broadly defined",
    "situations where a party is protected from liability even for serious wrongdoing, or where standard liability protections such as caps or exclusions are removed through carve-outs",

    # === LIABILITY LIMITATIONS & EXCLUSIONS ===
    "provisions that cap, restrict, or exclude what one party can recover for losses, including exclusions for lost profits, business disruption, or indirect damages",

    # === PENALTIES & INDEMNIFICATION ===
    "financial penalties, liquidated damages, or cost-recovery mechanisms that disproportionately burden one party, including penalties framed as pre-estimated compensation",

    # === ONE-SIDED / UNILATERAL OBLIGATIONS ===
    "provisions giving one party the power to change, override, or decide key contract terms without needing the other side's agreement, or where silence is treated as consent",

    # === TERMINATION RISKS ===
    "provisions allowing a party to end the contract without needing to show wrongdoing, including short or no notice requirements",
    "clauses defining what counts as a serious enough breach to end the contract, how much time is given to fix it, and which obligations continue once the contract ends",

    # === AUTO-RENEWAL TRAPS ===
    "clauses that renew the contract automatically unless a party opts out within a narrow window, especially where the renewal notice deadline is easy to miss",

    # === PAYMENT RISKS ===
    "payment conditions that depend on external approvals, disputed performance, or unilateral judgment calls, creating uncertainty about whether or when payment will occur",
    "clauses that allow previously paid money to be reclaimed, or that let one party adjust prices or costs without the other side's agreement",

    # === IP OWNERSHIP ===
    "clauses that transfer ownership of creative work, inventions, or developed materials to the other party, or grant broad, permanent usage rights without ongoing compensation",
    "clauses determining who owns data generated or processed during the contract, and risks from incorporating open-source components that could restrict future use or commercialization",

    # === CONFIDENTIALITY ISSUES ===
    "obligations to keep information secret, including how long those obligations last after the contract ends, what information is covered, and the consequences of disclosure",

    # === DATA & PRIVACY RISKS ===
    "requirements for how personal data is collected, processed, stored, or deleted, and who is responsible if a data breach occurs",

    # === JURISDICTION / DISPUTE RESOLUTION ===
    "provisions requiring disputes to be resolved through arbitration or in a specific location, or that limit a party's ability to bring or join legal action",

    # === REGULATORY & COMPLIANCE EXPOSURE ===
    "obligations to comply with anti-bribery, sanctions, export control, or other regulatory requirements that go beyond the core subject matter of the contract",

    # === EXCLUSIVITY & NON-COMPETE ===
    "restrictions that prevent a party from working with competitors, soliciting employees, or offering similar goods or services during or after the contract",

    # === WARRANTY DISCLAIMERS ===
    "language disclaiming standard warranties or limiting remedies for defective performance, including 'as-is' provisions or unusually short warranty periods",

    # === FORCE MAJEURE ABUSE ===
    "provisions excusing a party from performance due to external events, including how broadly those events are defined and whether they could be used to avoid normal obligations",

    # === UNFAIR OBLIGATIONS & TIMELINES ===
    "performance obligations described in vague or subjective terms, or deadlines and service levels that are difficult to meet and carry financial consequences if missed",

    # === AUDIT & RECORDS ===
    "rights allowing one party to examine the other's financial records or operational data, including how long that access continues after the contract ends",

    # === CONTRADICTORY / INCONSISTENT CLAUSES ===
    "sections of the contract that appear to conflict with each other, or language stating that one clause overrides others without clearly resolving the inconsistency",

    # === MANIPULATIVE / BOILERPLATE LEGAL WORDING ===
    "standard-looking boilerplate language that, on closer reading, significantly shifts risk, removes recourse, or creates obligations disproportionate to the purpose of the contract",

    # === FUNDING & DONOR COMPLIANCE ===
    "situations where the contract's obligations or payments depend on external funding, such as a grant or government award, that may not materialize or could be reduced or withdrawn",
    "additional reporting, audit, cost-allowability, or procurement compliance obligations imposed because the contract is funded by a grant, donor, or government program, including requirements that flow down from the original funding source",
]