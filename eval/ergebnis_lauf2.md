Cases: **55** (14 historisch, 41 synthetisch)  
Backend: `cli` - model `claude-sonnet-5` - threshold **0.7** (FLAKE needs +0.1)

| Class | Precision | Recall | F1 | Cases | Decided | Escalated |
|---|---|---|---|---|---|---|
| PRODUKTFEHLER | 1.00 | 0.67 | 0.80 | 15 | 15 | 0 |
| KAPUTTER_TEST | 0.69 | 1.00 | 0.81 | 25 | 22 | 3 |
| FLAKE | 1.00 | 0.55 | 0.71 | 15 | 11 | 4 |
| **macro** | **0.90** | **0.74** | **0.77** | 55 | 48 | 7 |

Coverage 87% - accuracy on decided cases 79% - **product bugs silently auto-rerun: 0**

**Confusion matrix** (rows = truth, columns = what the agent did)

| truth \ predicted | PRODUKTFEHLER | KAPUTTER_TEST | FLAKE | escalated |
|---|---|---|---|---|
| **PRODUKTFEHLER** | 10 | 5 | 0 | 0 |
| **KAPUTTER_TEST** | 0 | 22 | 0 | 3 |
| **FLAKE** | 0 | 5 | 6 | 4 |

**Threshold sweep**

| threshold | macro P | macro R | classes averaged | PRODUKTFEHLER recall | coverage | escalated | buried bugs |
|---|---|---|---|---|---|---|---|
| 0.50 | 0.82 | 0.69 | 3/3 | 0.67 | 96% | 4% | 0 |
| 0.55 | 0.84 | 0.70 | 3/3 | 0.67 | 95% | 5% | 0 |
| 0.60 | 0.83 | 0.70 | 3/3 | 0.67 | 93% | 7% | 0 |
| 0.65 | 0.84 | 0.71 | 3/3 | 0.67 | 91% | 9% | 0 |
| 0.70 <- | 0.90 | 0.74 | 3/3 | 0.67 | 87% | 13% | 0 |
| 0.75 | 0.90 | 0.75 | 3/3 | 0.71 | 85% | 15% | 0 |
| 0.80 | 0.90 | 0.75 | 3/3 | 0.71 | 84% | 16% | 0 |
| 0.85 | 0.90 | 0.62 | 3/3 | 0.69 | 73% | 27% | 0 |
| 0.90 | 0.89 | 0.60 | 2/3 ! | 0.80 | 56% | 44% | 0 |
| 0.95 | 0.94 | 0.58 | 2/3 ! | 0.75 | 36% | 64% | 0 |
