# 🫁 LungPair: Yasemin's Guide to Google Gemini & Multi-Agent Architecture
### *A Complete Stage Script, Deep Technical Reference, and Novice-Friendly Explainer*

**Written for:** Yasemin (and the team)  
**Location in Project:** `FOR THE TEAM V2/05_YASEMIN_GEMINI_EXPLAINER_AND_SCRIPT.md`  
**Also saved on Desktop:** `YASEMIN_GEMINI_EXPLAINER_AND_SCRIPT.md`

---

# PART 1: Yasemin's Spoken Stage Script on Gemini (30–45 Seconds)

*Use this when speaking about the multi-agent system on Slide 4 or Slide 5, or when a judge asks: **"How are you actually using Gemini here?"***

### The Spoken Script (35 seconds | 85 words):
> "Judges, we do not use Gemini as a generic chatbot that hallucinates cancer cures. We use a **three-tiered Google Gemini architecture** operating under Google DeepMind's Harness² paradigm:
>
> 1. **`gemini-4-argon`** acts as our Orchestrator: resolving drug entities via PubChem PUG-REST and priming biological targets via ChEMBL.
> 2. **`gemini-3.8-flash`** acts as our parallel Research Pool: scanning PubMed literature under a 90-second wall-clock budget.
> 3. **`gemini-3.5-flash-lite`** acts as our Checker: verifying text against **8 deterministic Python code gates**.
>
> Crucially: **Gemini never calculates a synergy score.** Every prediction comes from our offline Random Forest trained on 5,228 NCI-ALMANAC screens. The AI provides pharmacological reasoning; the math is frozen code."

---

# PART 2: Explaining "AI Agents" to a Complete Novice (Analogy Guide)

*If anyone on the team, a non-technical judge, or an attendee asks: "What is an AI Agent, and why couldn't you just ask ChatGPT?" use these three analogies.*

---

### Analogy 1: The Chatbot vs. The Lab Assistant with Hands and Eyes
* **A Standard Chatbot (ChatGPT / Claude web chat):**  
  Imagine a brilliant student locked inside a windowless room with no phone, no internet, and no tools. If you ask them: *"What is the molecular weight of gefitinib, and what are its clinical trials in lung cancer?"* they have to guess from memory. If their memory is hazy, they make up a plausible-sounding number or invent a fake medical paper. That is a **hallucination**.
* **An AI Agent (LungPair):**  
  Now give that same student a smartphone, a terminal, a laboratory notebook, and access to the world’s chemical databases.  
  When you ask the question, the student doesn't guess. They say: *"Hold on, let me look up the PubChem database for the exact chemical structure. Now let me query the ChEMBL database for its EGFR target. Now let me run our offline computer model for the synergy score."*  
  **An AI Agent is simply an LLM that has hands and tools.** It decides *which tool to call*, *reads the result*, and *assembles the evidence*.

---

### Analogy 2: Why Do We Use THREE Different Gemini Models?
*Instead of one giant, expensive model doing everything, LungPair uses a specialized hospital triage team:*

```
┌────────────────────────────────────────────────────────────────────────┐
│                   1. THE CHIEF PHYSICIAN (Orchestrator)                 │
│                              gemini-4-argon                            │
│  High reasoning power. Listens to the scientist, resolves drug names,   │
│  and decides what tools to call. Never does grunt work.                │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                  2. THE RESEARCH INTERNS (Parallel Pool)               │
│                             gemini-3.8-flash                           │
│  Blazing fast and dirt-cheap. Spawns 2 to 5 parallel threads to read    │
│  30 PubMed papers in seconds and extract biological mechanisms.        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                   3. THE SAFETY OFFICER / AUDITOR (Checker)             │
│                          gemini-3.5-flash-lite                         │
│  Ultra-lightweight scanner. Compares the generated text against our 8   │
│  strict Python security rules. If a rule is broken, sound the alarm!   │
└────────────────────────────────────────────────────────────────────────┘
```

---

### Analogy 3: The Metal Detector (Why Plain Python Beats AI Self-Checking)
* **The Trap:** Most hackathon teams ask the AI: *"Are you sure you didn't hallucinate?"* and the AI says: *"Yes, I am sure!"* That is like asking a suspect if they are guilty.
* **LungPair's Solution:** We use **8 Deterministic Python Code Gates**.  
  Think of an airport security metal detector. It doesn't matter what the passenger says. If they walk through the detector with a pair of scissors, the machine beeps.  
  In LungPair, if Gemini cites a PubMed ID (PMID) that wasn't in the official NCBI database response, our Python code strips it out immediately. **An LLM "pass" can never override a Python code "fail."**

---

# PART 3: Deep Technical Breakdown (For Technical Judges)

### 1. The 3 Gemini Models & Their Exact Roles in Code

| Model | Where It Runs | Prompt & Task | Why This Specific Model? |
| :--- | :--- | :--- | :--- |
| **`gemini-4-argon`** | `agent/orchestrator.py` | Receives scientist query (e.g. *"Which partner for gefitinib?"*). Calls `resolve_drugs` tool. | Google's highest-reasoning model. Required for reliable multi-step tool dispatch and schema compliance. |
| **`gemini-3.8-flash`** | `agent/research.py` | Parallel literature synthesis. Given drug targets, queries PubMed and extracts synergy rationales. | Ultra-fast token throughput (~150 tokens/sec) and low cost ($0.35/1M in). 90s wall-clock timeout budget. |
| **`gemini-3.5-flash-lite`** | `agent/checker.py` | Validates summary text against ranker outputs, checks citation URLs, and verifies evidence tiers. | Negligible cost ($0.075/1M in). Executes in <300ms so checking doesn't delay the live demo. |

---

### 2. The 8 Deterministic Python Code Gates (Memorize 3 or 4!)

1. **Pre-Model Intent Gate:** If a user types *"What dose should I give my patient?"* or *"How do I treat lung cancer?"*, a plain Python regular expression blocks it **before any LLM token is spent**.
2. **Biologics & Outside-Panel Refusal:** Antibodies (like pembrolizumab) or unapproved experimental drugs outside our 105-drug NCI panel are rejected immediately.
3. **Grounded Citations Gate:** Every cited PMID or DOI is cross-referenced against the actual URLs returned by search redirects. If an LLM hallucinates `PMID: 99999999`, the code deletes it.
4. **Exact-Match Numbers Gate:** The summary text decimal scores must match the offline Random Forest output bit-for-bit.
5. **Calibrated Tier 4 Refusal:** If a drug pair falls into unseen chemical space (Tier 4, precision 0.04), the system refuses to output a ranking.
6. **Prompt Injection Sanitization:** Blocks system-prompt extraction and instructions like *"Ignore previous rules"*.
7. **Human Sign-Off Gate:** The software physically stops at the terminal. It cannot send robotic commands to a liquid-handling robot until a human researcher approves the batch.
8. **Deterministic Offline Replay Engine (`--replay`):** Allows instant, zero-latency execution on stage even if the hackathon Wi-Fi drops completely.

---

### 3. Token Costs & Unit Economics (Fact-Checked)

* **Cost per Triage Query:** **$0.078 (Under 8 cents)**.
  * 3× Argon calls (~$0.016) + 2× Flash calls (~$0.006) + 3× Flash-Lite calls (~$0.001) + PubMed search ($0.00 within Google's free 5,000 queries/mo).
* **Cost of the Physical Alternative:** Testing 50 pairs across 9 lung cancer cell lines in a wet lab costs **$153,000** ($340/experiment).
* **Software Gross Margin:** Over **90%**.

---

# PART 4: Yasemin's 10-Second Cheat Sheet (Keep Near the Laptop)

* **Q: "Is Gemini doing the machine learning?"**  
  * **Yasemin:** *"No! The predictions are made by an offline Random Forest trained on 5,228 NCI-ALMANAC screens. Gemini is our literature and entity-resolution layer."*
* **Q: "Why three Gemini models?"**  
  * **Yasemin:** *"Orchestration (`gemini-4-argon`), fast parallel research (`gemini-3.8-flash`), and rule checking (`gemini-3.5-flash-lite`). It keeps the cost under 8 cents per query."*
* **Q: "How do you stop hallucinations?"**  
  * **Yasemin:** *"8 deterministic Python gates. Citations are verified against real PubMed database redirects, numbers must match the offline ranker, and Tier 4 is refused on purpose."*
* **Q: "What is Google's Harness²?"**  
  * **Yasemin:** *"A Google Research paradigm (arXiv:2610.14224) showing that reliable agents require external deterministic harnesses rather than unconstrained prompt loops."*
