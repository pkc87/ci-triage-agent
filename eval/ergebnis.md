Cases: **55** (14 historisch, 41 synthetisch)  
Backend: `cli` - model `claude-sonnet-5` - threshold **0.7** (FLAKE needs +0.1)

| Class | Precision | Recall | F1 | Cases | Decided | Escalated |
|---|---|---|---|---|---|---|
| PRODUKTFEHLER | 0.90 | 0.64 | 0.75 | 15 | 14 | 1 |
| KAPUTTER_TEST | 0.67 | 1.00 | 0.80 | 25 | 22 | 3 |
| FLAKE | 1.00 | 0.42 | 0.59 | 15 | 12 | 3 |
| **macro** | **0.86** | **0.69** | **0.71** | 55 | 48 | 7 |

Coverage 87% - accuracy on decided cases 75% - **product bugs silently auto-rerun: 0**

**Confusion matrix** (rows = truth, columns = what the agent did)

| truth \ predicted | PRODUKTFEHLER | KAPUTTER_TEST | FLAKE | escalated |
|---|---|---|---|---|
| **PRODUKTFEHLER** | 9 | 5 | 0 | 1 |
| **KAPUTTER_TEST** | 0 | 22 | 0 | 3 |
| **FLAKE** | 1 | 6 | 5 | 3 |

**Threshold sweep**

| threshold | macro P | macro R | classes averaged | PRODUKTFEHLER recall | coverage | escalated | buried bugs |
|---|---|---|---|---|---|---|---|
| 0.50 | 0.83 | 0.67 | 3/3 | 0.67 | 98% | 2% | 0 |
| 0.55 | 0.83 | 0.67 | 3/3 | 0.67 | 96% | 4% | 0 |
| 0.60 | 0.85 | 0.68 | 3/3 | 0.67 | 91% | 9% | 0 |
| 0.65 | 0.85 | 0.68 | 3/3 | 0.67 | 91% | 9% | 0 |
| 0.70 <- | 0.86 | 0.69 | 3/3 | 0.64 | 87% | 13% | 0 |
| 0.75 | 0.86 | 0.69 | 3/3 | 0.64 | 87% | 13% | 0 |
| 0.80 | 0.89 | 0.71 | 3/3 | 0.64 | 82% | 18% | 0 |
| 0.85 | 0.89 | 0.64 | 3/3 | 0.64 | 76% | 24% | 0 |
| 0.90 | 0.90 | 0.63 | 2/3 ! | 0.89 | 53% | 47% | 0 |
| 0.95 | 0.91 | 0.60 | 2/3 ! | 0.80 | 38% | 62% | 0 |
