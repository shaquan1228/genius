# Genius evals

The evals measure instruction variants on benchmark cases and compare them with stated uncertainty.

## Language

### Observations

**Case**:
One benchmark task in a dataset. The case is the sampling unit of every estimate.
_Avoid_: unit, sample, question, item

**Trial**:
One graded try at one case. A case holds one or more trials; the epoch is the trial's index.
_Avoid_: unit, attempt, sample

**Metric**:
A named number that a trial records, such as accuracy, elapsed seconds, or one check's pass.
_Avoid_: score, measure

**Run**:
All trials of one variant over one selection of cases. Cases can hold different trial counts and metrics.
_Avoid_: log, result

### Comparison

**Variant**:
A named set of instructions under evaluation.
_Avoid_: arm, condition, treatment

**Baseline**:
The variant that every other variant is contrasted against.
_Avoid_: control, reference

**Estimate**:
A metric's mean over cases, with its standard error and interval when two or more cases observe it.
_Avoid_: average, score

**Contrast**:
One variant's paired change from the baseline: per case, the difference of case means.
_Avoid_: diff, delta

**Objective**:
A metric that gates a verdict: the better direction, the loss it tolerates, and the gain that counts.
_Avoid_: limit, criterion, threshold

**Measurement**:
The confidence level and the objectives of one comparison.
_Avoid_: decision rule, policy

**Verdict**:
Improved, regressed, or inconclusive. Regressed: an objective is surely worse than its tolerance. Improved: no objective can be worse than its tolerance, and one gain is sure.
_Avoid_: result, outcome

## Relationships

- A **Run** holds **Cases**; each **Case** holds one or more **Trials**.
- A **Contrast** pairs the **Baseline** run with one other run over the same **Cases**.
- A **Verdict** reads only the **Contrast** estimates of the **Objectives**.

## Flagged ambiguities

- "Unit" named both the case (sampling unit) and one graded try. Resolved: **Case** and **Trial**.
- "Attempts" already names the agent's own retries inside one trial. Do not use it for trials.
- "Limit" already names execution limits (time, cost, messages). Do not use it for objectives.
