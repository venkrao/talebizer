# Spec Clarifications (v0.2)

## 1. Tail Scenario Volatility Source (§3.3)

### Decision

Use **realized volatility** for tail scenario generation.

```text
σ_tail = σ_realized
```

### Rationale

In a Talebian framework:

* **Implied volatility** represents the **market’s belief**
* **Realized volatility** approximates **empirical behavior**

Tail scenarios should model **what could actually occur**, not what the market prices.

Therefore:

```text
S_tail = S * exp(σ_realized * sqrt(T) * multiplier)
```

Where:

```
multiplier ∈ {2, 4, 6}
```

---

### Use of Implied Volatility

Implied volatility is used only for **pricing comparison**:

```text
vol_edge = σ_realized − σ_implied
```

Interpretation:

| Condition              | Interpretation             |
| ---------------------- | -------------------------- |
| σ_realized > σ_implied | options may be underpriced |
| σ_realized < σ_implied | options may be overpriced  |

---

# 2. Tail Efficiency (§4.3)

You are correct that **tail probability estimation is the hardest part**.

For **v0.1**, the best design choice is:

### Remove Tail Efficiency entirely.

Reason:

```text
tail probability estimation introduces subjective modeling
```

Any of the following would require heavy modeling:

* power-law fitting
* EVT (extreme value theory)
* jump diffusion processes

These are outside the scope of a **lightweight personal tool**.

Instead, the system should rely on **structural convexity metrics** that do not require probabilities.

---

# 3. Taleb Score (§8)

You're right: it was undefined.

Here is a **deterministic scoring rule**.

### Inputs

```
convexity_ratio
vol_edge
time_to_expiry
```

---

## 3.1 Convexity Score (0–50)

```
if convexity_ratio < 5 → 5
if 5–10 → 15
if 10–20 → 30
if 20–40 → 40
if >40 → 50
```

---

## 3.2 Volatility Edge Score (0–30)

```
vol_edge < -5% → 5
-5% to 0% → 10
0% to 5% → 20
>5% → 30
```

---

## 3.3 Time Horizon Score (0–20)

```
T < 30 days → 5
30–90 days → 10
90–180 days → 15
>180 days → 20
```

---

### Final Score

```
taleb_score =
convexity_score
+ vol_score
+ time_score
```

Range:

```
0–100
```

---

### Interpretation

| Score  | Interpretation    |
| ------ | ----------------- |
| 0–30   | weak convexity    |
| 30–60  | moderate          |
| 60–80  | strong            |
| 80–100 | extreme convexity |

---

# 4. Updated Core Metrics (Simplified)

Final **v0.2 metrics**:

```
intrinsic_value
time_value
convexity_ratio
vol_edge
taleb_score
```

Removed:

```
tail_efficiency
```

---

# 5. Core Philosophy (Now Explicit)

The system intentionally avoids estimating **true probabilities**.

Instead it focuses on **structural asymmetry**:

```
large potential payoff
relative to
small premium remaining
```

This reflects the approach discussed by
Nassim Nicholas Taleb in
Dynamic Hedging.

---

