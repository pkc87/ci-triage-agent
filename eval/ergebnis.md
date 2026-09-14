Cases: **47** (14 historisch, 33 synthetisch)  
Backend: `cli` - model `claude-sonnet-5` - threshold **0.7** (FLAKE needs +0.1)

| Class | Precision | Recall | F1 | Cases | Decided | Escalated |
|---|---|---|---|---|---|---|
| PRODUKTFEHLER | 1.00 | 0.53 | 0.70 | 15 | 15 | 0 |
| KAPUTTER_TEST | 0.67 | 1.00 | 0.80 | 25 | 22 | 3 |
| FLAKE | 1.00 | 0.33 | 0.50 | 7 | 6 | 1 |
| **macro** | **0.89** | **0.62** | **0.67** | 47 | 43 | 4 |

Coverage 91% - accuracy on decided cases 74% - **product bugs silently auto-rerun: 0**

**Confusion matrix** (rows = truth, columns = what the agent did)

| truth \ predicted | PRODUKTFEHLER | KAPUTTER_TEST | FLAKE | escalated |
|---|---|---|---|---|
| **PRODUKTFEHLER** | 8 | 7 | 0 | 0 |
| **KAPUTTER_TEST** | 0 | 22 | 0 | 3 |
| **FLAKE** | 0 | 4 | 2 | 1 |

**Threshold sweep**

| threshold | macro P | macro R | classes averaged | PRODUKTFEHLER recall | coverage | escalated | buried bugs |
|---|---|---|---|---|---|---|---|
| 0.50 | 0.89 | 0.61 | 3/3 | 0.53 | 98% | 2% | 0 |
| 0.55 | 0.89 | 0.61 | 3/3 | 0.53 | 96% | 4% | 0 |
| 0.60 | 0.89 | 0.62 | 3/3 | 0.53 | 91% | 9% | 0 |
| 0.65 | 0.89 | 0.62 | 3/3 | 0.53 | 91% | 9% | 0 |
| 0.70 <- | 0.89 | 0.62 | 3/3 | 0.53 | 91% | 9% | 0 |
| 0.75 | 0.90 | 0.63 | 3/3 | 0.57 | 89% | 11% | 0 |
| 0.80 | 0.90 | 0.64 | 3/3 | 0.58 | 83% | 17% | 0 |
| 0.85 | 0.91 | 0.63 | 3/3 | 0.64 | 74% | 26% | 0 |
| 0.90 | 0.89 | 0.57 | 2/3 ! | 0.70 | 62% | 38% | 0 |
| 0.95 | 1.00 | 1.00 | 2/3 ! | 1.00 | 34% | 66% | 0 |
