Cases: **47** (14 historisch, 33 synthetisch)  
Backend: `cli` - model `claude-sonnet-5` - threshold **0.7** (FLAKE needs +0.1)

| Class | Precision | Recall | F1 | Cases | Decided | Escalated |
|---|---|---|---|---|---|---|
| PRODUKTFEHLER | 0.91 | 0.71 | 0.80 | 15 | 14 | 1 |
| KAPUTTER_TEST | 0.72 | 0.95 | 0.82 | 25 | 22 | 3 |
| FLAKE | 1.00 | 0.33 | 0.50 | 7 | 6 | 1 |
| **macro** | **0.88** | **0.67** | **0.71** | 47 | 42 | 5 |

Coverage 89% - accuracy on decided cases 79% - **product bugs silently auto-rerun: 0**

**Confusion matrix** (rows = truth, columns = what the agent did)

| truth \ predicted | PRODUKTFEHLER | KAPUTTER_TEST | FLAKE | escalated |
|---|---|---|---|---|
| **PRODUKTFEHLER** | 10 | 4 | 0 | 1 |
| **KAPUTTER_TEST** | 1 | 21 | 0 | 3 |
| **FLAKE** | 0 | 4 | 2 | 1 |

**Threshold sweep**

| threshold | macro P | macro R | classes averaged | PRODUKTFEHLER recall | coverage | escalated | buried bugs |
|---|---|---|---|---|---|---|---|
| 0.50 | 0.85 | 0.64 | 3/3 | 0.67 | 96% | 4% | 0 |
| 0.55 | 0.84 | 0.64 | 3/3 | 0.67 | 94% | 6% | 0 |
| 0.60 | 0.87 | 0.65 | 3/3 | 0.67 | 91% | 9% | 0 |
| 0.65 | 0.87 | 0.65 | 3/3 | 0.67 | 91% | 9% | 0 |
| 0.70 <- | 0.88 | 0.67 | 3/3 | 0.71 | 89% | 11% | 0 |
| 0.75 | 0.88 | 0.67 | 3/3 | 0.71 | 89% | 11% | 0 |
| 0.80 | 0.87 | 0.67 | 3/3 | 0.71 | 87% | 13% | 0 |
| 0.85 | 0.82 | 0.57 | 2/3 ! | 0.77 | 81% | 19% | 0 |
| 0.90 | 0.93 | 0.63 | 2/3 ! | 0.90 | 62% | 38% | 0 |
| 0.95 | 0.97 | 0.67 | 2/3 ! | 1.00 | 38% | 62% | 0 |
