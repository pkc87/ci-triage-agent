Cases: **55** (14 historisch, 41 synthetisch)  
Backend: `stub` - model `keyword-rules` - threshold **0.7** (FLAKE needs +0.1)

| Class | Precision | Recall | F1 | Cases | Decided | Escalated |
|---|---|---|---|---|---|---|
| PRODUKTFEHLER |   -   |   -   |   -   | 15 | 0 | 15 |
| KAPUTTER_TEST | 1.00 | 1.00 | 1.00 | 25 | 17 | 8 |
| FLAKE | 1.00 | 1.00 | 1.00 | 15 | 6 | 9 |
| **macro** | **1.00** | **1.00** | **1.00** | 55 | 23 | 32 |

Coverage 42% - accuracy on decided cases 100% - **product bugs silently auto-rerun: 0**

**Confusion matrix** (rows = truth, columns = what the agent did)

| truth \ predicted | PRODUKTFEHLER | KAPUTTER_TEST | FLAKE | escalated |
|---|---|---|---|---|
| **PRODUKTFEHLER** | 0 | 0 | 0 | 15 |
| **KAPUTTER_TEST** | 0 | 17 | 0 | 8 |
| **FLAKE** | 0 | 0 | 6 | 9 |

**Threshold sweep**

| threshold | macro P | macro R | classes averaged | PRODUKTFEHLER recall | coverage | escalated | buried bugs |
|---|---|---|---|---|---|---|---|
| 0.50 | 0.75 | 0.47 | 2/3 ! | 0.00 | 98% | 2% | 0 |
| 0.55 | 0.75 | 0.47 | 2/3 ! | 0.00 | 98% | 2% | 0 |
| 0.60 | 0.75 | 0.47 | 2/3 ! | 0.00 | 98% | 2% | 0 |
| 0.65 | 1.00 | 1.00 | 2/3 ! |   -   | 42% | 58% | 0 |
| 0.70 <- | 1.00 | 1.00 | 2/3 ! |   -   | 42% | 58% | 0 |
| 0.75 | 1.00 | 1.00 | 2/3 ! |   -   | 27% | 73% | 0 |
| 0.80 | 1.00 | 1.00 | 2/3 ! |   -   | 27% | 73% | 0 |
| 0.85 | 1.00 | 1.00 | 2/3 ! |   -   | 27% | 73% | 0 |
| 0.90 | 1.00 | 1.00 | 1/3 ! |   -   | 16% | 84% | 0 |
| 0.95 | 0.00 | 0.00 | 0/3 ! |   -   | 0% | 100% | 0 |
