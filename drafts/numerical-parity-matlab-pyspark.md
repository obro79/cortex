# Numerical Parity Is the Hard Part: Rewriting MATLAB in PySpark

When I was working at RBC, I helped rewrite a legacy quantitative finance pipeline from MATLAB into Python/PySpark on Databricks.

The goal sounded simple: make it faster.

The old process ran on-prem and scored investment factors across financial time series data. At a high level, it took in prices, market caps, securities, dates, and factor inputs, then ran a long sequence of regression, filtering, scoring, normalization, de-meaning, and sector/country neutralization. The final output was a set of factor z-scores consumed by quantitative researchers.

A historical backfill for a new factor could take week-scale effort in the legacy flow. In the rewritten system, that same kind of run could complete in about a minute.

That speedup was real. It mattered.

It was also not the hard part.

The hard part was getting people to trust the new numbers.

The MATLAB system was slow, but it had history behind it. Researchers had used it for years. Downstream workflows expected its outputs. People knew what the numbers should look like. They knew which factors were weird, which regions behaved differently, and which values were worth questioning.

The PySpark rewrite had none of that trust.

It could be faster, cleaner, and more scalable, but none of that mattered if the z-scores were wrong. In a quantitative finance pipeline, small numerical differences can propagate. A tiny score difference can flow into downstream calculations, portfolio construction, and ultimately asset allocation.

So the real task was not:

> Can we make this run faster?

It was:

> Can we prove the distributed rewrite produces the same outputs as the legacy MATLAB system?

That was the project.

## The First Comparison Was Brutal

In one early comparison, almost none of the final z-scores matched even to one decimal place.

That sounds like a clean failure. It was not. The painful part was that the mismatch did not tell us where the problem was.

It could have been the input data.

The MATLAB process and Databricks process were not reading data through the same path. The old system had years of source-specific behavior. Some factor inputs came from one place. Some came from another. Some date ranges had different historical sources. Some securities existed in one source but not another.

It could have been the output data.

We were comparing scores across securities, dates, factors, regions, and investment universes. If either side had missing rows, different identifiers, different dates, or different sorting, the comparison itself could be lying.

It could have been a MATLAB-versus-Python difference.

NaN handling. Floating point order of operations. Sorting stability. Linear algebra routines. Matrix shape assumptions. Default degrees of freedom. These details are easy to ignore until you are trying to match an old numerical system exactly.

It could have been a distributed-systems issue.

PySpark makes joins, grouping, partitioning, driver memory, worker memory, and execution boundaries explicit. A serial MATLAB process can hide assumptions in the shape of arrays and loop order. A distributed rewrite forces those assumptions into the open.

Or it could have been a real algorithmic bug.

That was the core debugging problem. The first question was not "which line is wrong?"

The first question was:

> Which layer are we even debugging?

## Numerical Parity Is Not One Check

Before this project, I thought of numerical parity as a final comparison. Run the old system. Run the new system. Compare outputs.

That is not enough.

A final score is too far downstream. By the time a z-score differs, the root cause may be buried ten transformations earlier.

For this pipeline, the output depended on a long chain:

1. source data selection
2. identifier mapping
3. date alignment
4. universe construction
5. missing-value handling
6. factor-specific configuration
7. preliminary statistics
8. winsorization
9. regression and neutralization
10. degrees-of-freedom logic
11. t-to-z conversion
12. scaling
13. final de-meaning
14. output formatting

If the final score differed, any one of those layers could be responsible.

Worse, the layers interact. A missing security changes the mean. That changes standardization. That changes the regression. That changes residuals. That changes the final z-score. By the time you see the final mismatch, the original cause is gone.

So numerical parity had to become a debugging system.

The questions were:

- Are both systems reading the same input rows?
- Are the same securities present?
- Are the same dates present?
- Are missing values handled the same way?
- Are the same factor-specific flags applied?
- Are intermediate values still matching?
- Are final differences just floating point noise, or are they structural?

That is a very different problem from "does this output table match?"

By the end, the validation surface was enormous. Across historical dates, securities, regions, and factors, we validated roughly 500 million score rows. That scale changes the debugging problem. You are no longer looking for one bad value. You are looking for the pattern that explains millions of differences.

## The Black Box Problem

I also had to accept that I did not fully understand the legacy process at the beginning.

That is normal in legacy systems, but it matters. Some behavior lived in MATLAB code. Some lived in configuration. Some lived in table mappings. Some lived in naming conventions. Some lived in the heads of people who had worked with the system for years.

At a high level, I knew the pipeline scored factors. But the details were not obvious:

- Which data source was authoritative for each factor?
- Which factors had special handling?
- Which regions needed country-level neutralization?
- Which missing values were expected?
- Which securities should be included?
- Which production tables contained raw scores versus transformed scores?

That made the work feel less like rewriting code and more like archaeology.

The goal was not just to implement a cleaner version of the pipeline. The goal was to uncover enough of the old system's behavior to reproduce it.

This is where a lot of rewrites go wrong. You assume the old system is messy, so you try to replace it with something cleaner. Sometimes that is right. But if the first goal is migration, the old behavior is the contract.

Even the weird parts.

Especially the weird parts.

## The Validation Report

The first useful artifact was a Python notebook that compared golden MATLAB outputs against the PySpark outputs.

It generated row-level failure counts, missing-data summaries, coverage metrics, decimal-place agreement buckets, histograms, and scatter plots. Instead of staring at raw tables, we could see where the systems disagreed and how badly.

A very simplified version looked like this:

```text
factor      universe      rows      missing_new      missing_old      within_1dp      within_4dp      max_abs_diff
value       Canada        1.2M      0.03%           0.02%            98.7%           99.99%          1.2e-12
quality     US            2.8M      0.01%           0.01%            92.4%           99.95%          4.8e-11
momentum    Global        5.1M      1.40%           0.02%            12.2%           45.00%          3.2e+00
```

The numbers above are illustrative. The structure is what mattered.

The report made it possible to separate different failure modes:

- tiny floating point drift
- missing rows
- broken factor coverage
- bad source data
- region-specific failures
- structural output shifts

The code idea was simple:

```python
def compare_outputs(actual, expected, *, atol, rtol):
    aligned = align_on_keys(
        actual,
        expected,
        keys=["date", "security_id", "factor", "universe"],
    )

    diff = abs(aligned.actual_score - aligned.expected_score)
    tolerance = atol + rtol * abs(aligned.expected_score)

    failures = aligned[diff > tolerance]

    return {
        "rows": len(aligned),
        "failed_rows": len(failures),
        "max_abs_diff": diff.max(),
        "coverage": 1 - len(failures) / len(aligned),
    }
```

The real system was obviously more much complicated. But the principle was the same:

1. align the rows
2. define the tolerance
3. summarize the failures
4. make the mismatch explainable

That last point was the important one.

The report was not just for me. It was how we got buy-in. Quantitative researchers did not need to read every line of PySpark code. They needed to see where the systems matched, where they diverged, and whether the remaining differences were explainable.

## Final Outputs Were Not Enough

The first validation report compared final outputs. That was necessary, but it was too coarse.

If a final z-score differs, you still do not know why.

So we went deeper. We exported a richer MATLAB baseline: 26 intermediate columns, including actuals, weights, preliminary statistics, residuals, degrees of freedom, z-scores, and final scores. Those intermediates were written to parquet and compared against the Python implementation step by step.

That changed the debugging loop.

Instead of asking:

> Why is this final score different?

we could ask:

> At which stage did this row first diverge?

That was the turning point.

For a pipeline with regression, filtering, scoring, normalization, de-meaning, and neutralization, final-output comparison is like debugging a production outage with only the final HTTP response. It tells you something is wrong. It does not tell you where to look.

Intermediate checkpoints give you the stack trace.

Useful checkpoints included:

- raw actuals
- weights
- sector/country labels
- preliminary means
- preliminary standard deviations
- winsorized values
- regression residuals
- degrees of freedom
- transformed z-scores
- final scores

Once those existed, debugging became mechanical:

- Do actuals match?
- Do weights match?
- Does the preliminary mean match?
- Does the winsorized value match?
- Does the regression residual match?
- Does the final score match?

The first "no" narrowed the search space.

That is the difference between validation as a final gate and validation as an engineering tool.

## Source Data Was a First-Class Problem

One mistake I would avoid next time is treating input data as a given.

It is tempting to focus on the algorithm. If the output does not match, the scoring logic must be wrong.

That assumption only holds if both systems are computing from the same inputs.

In practice, source data was one of the biggest sources of ambiguity. The old and new systems could reach similar conceptual data through different paths. Some factors existed in one table but not another. Some historical ranges used different sources. Some securities were filtered differently. Some rows existed in one system and silently disappeared in another.

That creates a dangerous debugging loop:

1. Compare outputs.
2. See mismatch.
3. Change algorithm.
4. Rerun.
5. Still mismatch.
6. Later discover the inputs never matched.

At that point, the algorithm debugging was contaminated.

If I were doing this again, I would start with a formal input contract. For every validation run, I would store:

- run ID
- region/universe
- factor list
- date range
- exact input rows used by MATLAB
- exact input rows used by PySpark
- source metadata
- row counts by factor/date/security
- missingness summaries

Before asking whether the algorithm matched, I would ask whether the two systems were solving the same problem.

That sounds obvious now. It was not obvious enough at the time.

## The Edge Cases Were the Real Work

Once the validation harness existed, the work became a long process of eliminating ambiguity.

Some edge cases were expected:

- NaN handling
- zero weights
- insufficient observations
- missing securities
- sorting stability
- floating point order of operations

Others were more subtle.

One of the hardest bugs came from a country-level neutralization configuration. A region looked like it should behave as a single-country universe, but a few securities were legally domiciled elsewhere. That changed the dummy variables entering the regression, shifted the regression output, and caused the final scores to diverge.

This is the kind of bug that makes parity work painful.

Nothing crashes. The output table looks plausible. The scores are not obviously absurd. But the regression is solving a slightly different problem than the legacy system.

That is enough to break parity.

Other fixes were similarly specific. Some degrees-of-freedom calculations depended on whether sector and country dummy variables were both active. Some counts needed to use non-zero actuals, not total group membership. Some zero-degree-of-freedom cases had to produce missing values rather than being clamped. Some de-meaning needed to ignore missing values exactly the way MATLAB did.

None of those sound dramatic in isolation.

Together, they were the difference between "close" and "trusted."

That changed how I think about edge cases. In a system like this, edge cases are not weird optional behavior. They are part of the contract.

If people have trusted the old output for years, then the edge cases are part of what they trust.

## Seven Small Fixes Beat One Big Rewrite

The path to parity was not one dramatic breakthrough.

It was a sequence of small fixes.

The fixes were things like:

- matching a conditional degrees-of-freedom formula
- counting non-zero observations instead of total group members
- applying group filters based on valid observations
- preserving missing-value behavior in zero-degree-of-freedom cases
- making final de-meaning NaN-aware
- matching the legacy t-to-z transform
- computing degrees of freedom for groups that were later dropped

These are not glamorous fixes.

But this is what real migration work looks like. The old system's behavior is encoded in dozens of small decisions. If you miss one, the output drifts. If you miss several, the system looks completely wrong.

The strange part is that early on, a migration can look hopeless. If almost nothing matches, it feels like the rewrite is fundamentally broken. But often the problem is not one giant flaw. It is a collection of small behavioral mismatches compounding through the pipeline.

That is why the validation harness mattered. It gave us a way to turn a giant mismatch into a list of smaller mismatches.

And smaller mismatches can be fixed.

## Distributed Systems Expose Hidden Assumptions

The PySpark rewrite also surfaced assumptions that were easy to miss in MATLAB.

The legacy process effectively worked one date/factor cross-section at a time. For a given date and factor, it would compute statistics, run regressions, and produce scores for that cross-section. Another date did not depend on it. Another factor did not depend on it.

That made the workload parallelizable.

But "parallelizable" does not mean "any parallel implementation is equivalent."

If a distributed implementation accidentally groups data at the wrong level, it can compute perfectly valid statistics over the wrong population. For example, pooling multiple dates together before computing means or regressions still produces numbers. They are just not the numbers MATLAB computed.

This class of bug is easy to miss because nothing fails loudly.

The pipeline runs.

The output schema is correct.

The table has scores.

The only thing telling you something is wrong is the validation report.

That is why distributed rewrites need to define the unit of independence explicitly:

- What is the smallest independent computation?
- Which keys define a group?
- Which operations can cross groups?
- Which operations must stay inside a group?
- Which intermediate values should be scalar per group?

For this pipeline, the answer was not "run Spark over the whole table."

The answer was:

> preserve the same cross-sectional boundaries as MATLAB, then parallelize across those boundaries.

That distinction matters.

## Driver Bottlenecks Are Design Problems

Another lesson: scaling up the cluster does not automatically fix a bad data movement pattern.

At one point, a performance investigation pointed to a familiar Spark problem: collecting too much distributed data back to the driver. The pipeline could use a large cluster, but if each parallel task materialized millions of rows on the driver, the driver became the bottleneck.

The symptoms were exactly what you would expect:

- driver memory pressure
- serialization overhead
- network saturation into one node
- garbage collection pressure
- parallel jobs fighting for the same driver resources

The tempting fix is to increase cluster size.

Sometimes that helps.

But if the architecture still funnels distributed data into one process, more workers can just make the bottleneck louder.

The better question is:

> Where should this computation live?

If the data is distributed and the computation can be done per group, the work should stay close to the workers. That means designing the pipeline around grouped execution, not collecting everything back into Python because it is easier to reason about locally.

This is where the migration became more than a language rewrite. It was not MATLAB-to-Python. It was single-machine assumptions to distributed-system design.

## Optimize Enough to Validate

There is a common rule:

> Validate first, then optimize.

In principle, I agree.

In practice, this project taught me a more nuanced version:

> Do not optimize blindly, but make the feedback loop fast enough that validation is practical.

If every fix requires waiting hours, the validation loop is broken. You lose context. You batch changes together. You stop testing small hypotheses. Debugging becomes slow and sloppy because the system punishes iteration.

Once the Databricks/PySpark path was fast enough, the work changed. We could make a fix, rerun the pipeline, regenerate the report, and inspect the result while the hypothesis was still fresh.

That mattered.

Performance was a debugging enabler.

This is the part I would keep if I did the project again. I would still avoid optimizing random code before I understood correctness. But I would absolutely invest early in making the validation loop fast.

Time-to-validate-a-fix should have been a first-class metric.

## The Test Strategy Was Different for Data

The test strategy looked different from a normal application test suite.

For application code, I usually think in terms of unit tests, integration tests, and end-to-end tests. That still applied, but each layer had a specific purpose here.

For this project:

- unit tests covered deterministic math and edge cases
- regression tests covered known MATLAB parity behaviors
- integration tests covered config wiring and data shape expectations
- Databricks runs covered distributed execution
- validation reports supported researcher buy-in and exploratory debugging

The key realization was that numerical precision should not live only at the end-to-end layer.

If you only test precision after a full distributed run, failures are too expensive and too hard to localize.

The deterministic math had to be testable without Spark. That meant having a Python core that could run locally against fixtures. Spark still mattered, but it was not the right tool for every validation question.

That separation made debugging cleaner:

- If a local parity test failed, the algorithm was wrong.
- If local parity passed but Databricks failed, the issue was likely data loading, grouping, distributed execution, or environment.
- If raw MATLAB parity passed but production-table comparison failed, the issue might be downstream transformations.

That separation was the difference between debugging one huge system and debugging layers.

## Raw Output and Production Output Are Not the Same Thing

Another thing I would formalize earlier: raw-output parity and production-table parity are different.

The raw MATLAB output was the correct target for algorithm validation. That is what the new scoring engine needed to reproduce.

But the downstream production table was not necessarily raw MATLAB output. There could be storage transformations, rounding, overrides, deletions, backfills, and other production-specific behavior between the scoring step and the table people queried.

If you compare the new raw output directly against a downstream production table, a mismatch might not mean the scoring algorithm is wrong. It might mean the production table has additional transformations.

That distinction matters because otherwise you mix two separate questions:

1. Did the new algorithm reproduce MATLAB?
2. Did the new pipeline reproduce every downstream production transformation?

Both questions matter.

They should not be debugged as one question.

If I were designing the validation from scratch, I would make the layers explicit:

- MATLAB raw output vs Python raw output
- Python raw output vs PySpark distributed output
- raw output vs transformed production-equivalent output
- production-equivalent output vs production table

Each comparison answers a different question.

Collapsing them into one comparison makes every mismatch harder to explain.

## What I Would Do Differently

The biggest thing I would change is the validation setup.

We captured golden final outputs from MATLAB. That was necessary, but it was not enough.

If I were doing it again, I would capture golden inputs from the start. That would let us separate data mismatches from algorithm mismatches much earlier.

I would also capture intermediate checkpoints earlier. We eventually did this, and it was one of the highest-leverage parts of the project. I just wish we had treated it as foundational from day one.

A better validation framework would include:

- run IDs for every comparison
- versioned golden inputs
- versioned golden outputs
- intermediate checkpoint tables
- row-level diff reports
- per-factor and per-universe summaries
- explicit missing-data metrics
- explicit coverage metrics
- small synthetic fixtures for known edge cases

The most important design goal would be source-of-error isolation.

Every validation layer should shrink the search space.

Instead of asking:

> Why is this final score different?

the system should help answer:

> Did this diverge at input loading, transformation, regression, scoring, or output formatting?

That is the level of precision you need if you want people to trust a rewrite.

## What This Changed About How I Think

This project changed how I think about legacy migrations.

I used to think the hard part was understanding the old code and rebuilding it in a better stack.

That is part of it.

But the deeper problem is trust.

The old system has known behavior. It may be slow. It may be ugly. It may be full of strange branches and undocumented assumptions. But it has one advantage: people already believe it.

The new system has to earn that belief.

You do that by reducing ambiguity:

- prove the inputs match
- prove the intermediate states match
- prove the final outputs match
- prove the edge cases match
- prove the distributed execution preserves the same mathematical boundaries
- prove the remaining differences are understood

Only then does performance matter.

The Databricks/PySpark rewrite made the pipeline dramatically faster. But the validation work made it usable. Without numerical parity, the speedup would have been an interesting benchmark and nothing more.

A faster rewrite is not an upgrade until people can trust it.

Correctness is what lets performance matter.
