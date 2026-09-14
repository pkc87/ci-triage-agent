Cases: **14** (14 historisch)  
Backend: `stub` - model `keyword-rules` - threshold **0.7** (FLAKE needs +0.1)

| Class | Precision | Recall | F1 | Cases | Decided | Escalated |
|---|---|---|---|---|---|---|
| PRODUKTFEHLER | 0.00 | 0.00 | 0.00 | 0 | 0 | 0 |
| KAPUTTER_TEST | 1.00 | 1.00 | 1.00 | 14 | 14 | 0 |
| FLAKE | 0.00 | 0.00 | 0.00 | 0 | 0 | 0 |
| **macro** | **1.00** | **1.00** | **1.00** | 14 | 14 | 0 |

Coverage 100% - accuracy on decided cases 100% - **product bugs silently auto-rerun: 0**

**Confusion matrix** (rows = truth, columns = what the agent did)

| truth \ predicted | PRODUKTFEHLER | KAPUTTER_TEST | FLAKE | escalated |
|---|---|---|---|---|
| **PRODUKTFEHLER** | 0 | 0 | 0 | 0 |
| **KAPUTTER_TEST** | 0 | 14 | 0 | 0 |
| **FLAKE** | 0 | 0 | 0 | 0 |

**Threshold sweep**

| threshold | macro P | macro R | PRODUKTFEHLER recall | coverage | escalated | buried bugs |
|---|---|---|---|---|---|---|
| 0.50 | 1.00 | 1.00 | 0.00 | 100% | 0% | 0 |
| 0.55 | 1.00 | 1.00 | 0.00 | 100% | 0% | 0 |
| 0.60 | 1.00 | 1.00 | 0.00 | 100% | 0% | 0 |
| 0.65 | 1.00 | 1.00 | 0.00 | 100% | 0% | 0 |
| 0.70 <- | 1.00 | 1.00 | 0.00 | 100% | 0% | 0 |
| 0.75 | 1.00 | 1.00 | 0.00 | 50% | 50% | 0 |
| 0.80 | 1.00 | 1.00 | 0.00 | 50% | 50% | 0 |
| 0.85 | 1.00 | 1.00 | 0.00 | 50% | 50% | 0 |
| 0.90 | 1.00 | 1.00 | 0.00 | 50% | 50% | 0 |
| 0.95 | 0.00 | 0.00 | 0.00 | 0% | 100% | 0 |
