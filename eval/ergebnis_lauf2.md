Cases: **47** (14 historisch, 33 synthetisch)  
Backend: `cli` - model `claude-sonnet-5` - threshold **0.7** (FLAKE needs +0.1)

| Class | Precision | Recall | F1 | Cases | Decided | Escalated |
|---|---|---|---|---|---|---|
| PRODUKTFEHLER | 1.00 | 0.73 | 0.85 | 15 | 15 | 0 |
| KAPUTTER_TEST | 0.73 | 1.00 | 0.85 | 25 | 22 | 3 |
| FLAKE | 1.00 | 0.33 | 0.50 | 7 | 6 | 1 |
| **macro** | **0.91** | **0.69** | **0.73** | 47 | 43 | 4 |

Coverage 91% - accuracy on decided cases 81% - **product bugs silently auto-rerun: 0**

**Confusion matrix** (rows = truth, columns = what the agent did)

| truth \ predicted | PRODUKTFEHLER | KAPUTTER_TEST | FLAKE | escalated |
|---|---|---|---|---|
| **PRODUKTFEHLER** | 11 | 4 | 0 | 0 |
| **KAPUTTER_TEST** | 0 | 22 | 0 | 3 |
| **FLAKE** | 0 | 4 | 2 | 1 |

**Threshold sweep**

| threshold | macro P | macro R | classes averaged | PRODUKTFEHLER recall | coverage | escalated | buried bugs |
|---|---|---|---|---|---|---|---|
| 0.50 | 0.89 | 0.67 | 3/3 | 0.73 | 96% | 4% | 0 |
| 0.55 | 0.88 | 0.67 | 3/3 | 0.73 | 94% | 6% | 0 |
| 0.60 | 0.91 | 0.69 | 3/3 | 0.73 | 91% | 9% | 0 |
| 0.65 | 0.91 | 0.69 | 3/3 | 0.73 | 91% | 9% | 0 |
| 0.70 <- | 0.91 | 0.69 | 3/3 | 0.73 | 91% | 9% | 0 |
| 0.75 | 0.91 | 0.69 | 3/3 | 0.73 | 89% | 11% | 0 |
| 0.80 | 0.92 | 0.70 | 3/3 | 0.77 | 85% | 15% | 0 |
| 0.85 | 0.58 | 0.59 | 3/3 | 0.77 | 81% | 19% | 0 |
| 0.90 | 0.63 | 0.62 | 3/3 | 0.88 | 60% | 40% | 0 |
| 0.95 | 0.65 | 0.67 | 3/3 | 1.00 | 47% | 53% | 0 |
