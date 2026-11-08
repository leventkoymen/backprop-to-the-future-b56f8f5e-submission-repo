# LungPair: Yasemin's 3D Live Demonstration Script (40 Seconds)

**Role:** 3D Molecular & Synergy Landscape Lead  
**Segment:** Slide 5: The Agent at Work [1:45 – 2:25] (40-second stage demo)  
**URL on Presenter Laptop:** `http://127.0.0.1:5173` (Pre-loaded in Chrome)  
**Stage Position:** Stand beside Yong at the laptop. Keep hands ready on keyboard keys: `1`, `2`, `3`, `H`, `F`, `Space`, `Arrow keys`.

---

## The Handover Cue (Listen for Yong)
* **Yong says on the mic:**  
  > *"...Let's run a real query: Which partner should a lab screen with gefitinib next? Yasemin, take them inside the biological landscape."*
* **Stage Action:** *Step up to the screen. Take the handheld mic smoothly.*

---

## Spoken Script & Key-by-Key Stage Actions (40 Seconds)

### [1:45 – 1:58] Scene 1: The 5,228-Pair Haystack (13 seconds)
* **Key Action:** **Press `1`**, then **Press `A`** *(Angles the camera into 3D)*, then **Press `H`** *(Lights up the hits)*.  
* **Visual on Screen:** All 5,228 column bars appear; pressing `H` instantly illuminates the 172 gold/teal synergy hits.

> "Thanks, Yong.
>
> What you're seeing here is our 3D landscape of **every single one of the 5,228 drug combinations** measured in NCI-ALMANAC across 9 lung cancer cell lines.
>
> `[PRESS 'H' TO LIGHT UP HITS]`
> 
> When we light up the hits, you see the reality facing bench scientists: **only 172 pairs—just 3.3%—show validated synergy.** Over 96% of these columns are expensive biological dead ends."

---

### [1:58 – 2:12] Scene 2: Multi-Agent Triage & 3D Molecular Structures (14 seconds)
* **Key Action:** **Press `2`** *(Switches to Scene 2)*, then **Press `F`** *(Focuses camera directly on the gefitinib doublet)*, then **Click the drug name / SDF** *(Shows 3D molecular stick model)*.  
* **Visual on Screen:** Camera zooms into the gefitinib candidate column; side panel displays the 3D chemical structure pulled from PubChem.

> `[PRESS '2' THEN 'F']`
>
> "*Now, judges, you might ask: 'Is this an abstract prediction, or real pharmacology?'*
> 
> When our orchestrator resolves gefitinib, it doesn't just score the doublet. It retrieves the **3D conformer from PubChem** and primes the **EGFR kinase target via ChEMBL**. 
> 
> `[PRESS 'SPACEBAR' TO SIGN OFF]`
> 
> As Yong showed on the terminal, our 8 Python gates verify the citations, and **I press Space to sign off** before any screening batch is sealed."

---

### [2:12 – 2:25] Scene 3: Empirical Dose-Reachability Surface (13 seconds)
* **Key Action:** **Press `3`** *(Switches to Scene 3)*, then **Press `Left/Right Arrow`** *(Steps through cell lines)*.  
* **Visual on Screen:** The 3D curved dose-response surface appears over the Bliss independence baseline.

> `[PRESS '3']`
>
> "Finally, in Scene 3, we show the **empirical 3D dose-response surface**. 
> 
> Prior models predict single numbers that fail in the clinic because doses aren't reachable. We map volume over the **Bliss independence manifold** to verify that synergy occurs within clinically achievable plasma concentrations (C_max).
> 
> Back to Theodore for the health economics."

---

## Yasemin's Presenter Quick-Reference Card

| Timing | Press Key | What Happens on Screen | What to Say (Core 1-Liner) |
| :--- | :---: | :--- | :--- |
| **0:00** | **`1`** + **`A`** | 3D Haystack angles into view | *"5,228 combinations tested across 9 lung lines."* |
| **0:05** | **`H`** | 172 synergy hits light up | *"Only 172 pairs (3.3%) show synergy—96% dead ends."* |
| **0:13** | **`2`** + **`F`** | Camera zooms to Gefitinib candidate | *"PubChem 3D structures + ChEMBL target priming."* |
| **0:22** | **`Space`** | Batch approved; JSONL receipt | *"Mandatory human sign-off before robotic plate setup."* |
| **0:27** | **`3`** | 3D Dose-Response Surface appears | *"Mapping reachability over Bliss independence."* |
| **0:40** | — | Hands off to Theodore | *"Back to Theodore for health economics."* |

---

## 3 Predicted Judge Questions Specifically for Yasemin

#### 1. André Shamsabadi (Isomorphic Labs): *"Where do the 3D molecular structures come from, and are they docked into the target?"*
> **Yasemin's Winning Answer (10 seconds):**  
> *"The 3D coordinates are 3D SDF conformers fetched via the PubChem PUG-REST API. We display ligand geometry and verify functional groups via RDKit SMARTS matching. We do not simulate protein-ligand docking live on stage—our target priming comes from verified ChEMBL bioassays."*

#### 2. Francesco Farina (Basecamp Research): *"What does the surface in Scene 3 actually represent?"*
> **Yasemin's Winning Answer (10 seconds):**  
> *"It plots the empirical 3x3 and 4x4 dose-combination grid from NCI-ALMANAC. The wireframe represents the Bliss independence expectation; the height above the surface is empirical excess growth inhibition. If the peak sits at toxic concentrations, the pair is de-prioritized."*

#### 3. Diana Cojocaru (UCL): *"Can you toggle between different cell lines in the viewer?"*
> **Yasemin's Winning Answer (10 seconds):**  
> *`[PRESS LEFT/RIGHT ARROW]` "Yes! Pressing the arrow keys steps through all 9 NSCLC cell lines (like A549, NCI-H23, HOP-62), allowing the researcher to immediately check whether synergy is cell-line specific or broadly conserved."*
