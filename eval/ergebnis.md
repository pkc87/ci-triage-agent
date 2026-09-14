Cases: **45** (14 historisch, 31 synthetisch)  
Backend: `cli` - model `claude-sonnet-5` - threshold **0.7** (FLAKE needs +0.1)

| Class | Precision | Recall | F1 | Cases | Decided | Escalated |
|---|---|---|---|---|---|---|
| PRODUKTFEHLER | 1.00 | 0.79 | 0.88 | 15 | 14 | 1 |
| KAPUTTER_TEST | 0.78 | 1.00 | 0.88 | 25 | 21 | 4 |
| FLAKE | 1.00 | 0.40 | 0.57 | 5 | 5 | 0 |
| **macro** | **0.93** | **0.73** | **0.78** | 45 | 40 | 5 |

Coverage 89% - accuracy on decided cases 85% - **product bugs silently auto-rerun: 0**

**Confusion matrix** (rows = truth, columns = what the agent did)

| truth \ predicted | PRODUKTFEHLER | KAPUTTER_TEST | FLAKE | escalated |
|---|---|---|---|---|
| **PRODUKTFEHLER** | 11 | 3 | 0 | 1 |
| **KAPUTTER_TEST** | 0 | 21 | 0 | 4 |
| **FLAKE** | 0 | 3 | 2 | 0 |

**Threshold sweep**

| threshold | macro P | macro R | classes averaged | PRODUKTFEHLER recall | coverage | escalated | buried bugs |
|---|---|---|---|---|---|---|---|
| 0.50 | 0.93 | 0.73 | 3/3 | 0.79 | 91% | 9% | 0 |
| 0.55 | 0.93 | 0.73 | 3/3 | 0.79 | 89% | 11% | 0 |
| 0.60 | 0.93 | 0.73 | 3/3 | 0.79 | 89% | 11% | 0 |
| 0.65 | 0.93 | 0.73 | 3/3 | 0.79 | 89% | 11% | 0 |
| 0.70 <- | 0.93 | 0.73 | 3/3 | 0.79 | 89% | 11% | 0 |
| 0.75 | 0.93 | 0.73 | 3/3 | 0.79 | 89% | 11% | 0 |
| 0.80 | 0.94 | 0.74 | 3/3 | 0.83 | 84% | 16% | 0 |
| 0.85 | 0.94 | 0.69 | 3/3 | 0.83 | 82% | 18% | 0 |
| 0.90 | 1.00 | 1.00 | 2/3 ! | 1.00 | 56% | 44% | 0 |
| 0.95 | 1.00 | 1.00 | 2/3 ! | 1.00 | 44% | 56% | 0 |
