# Skill Architecture Best Practices

> Provide this file to an agent alongside the `skill-creator` skill when creating a new skill.
> These principles are drawn from analysis of the SKILL.md format internals and should be
> applied as a checklist and design lens throughout the skill-creation process.

---

## Core Mental Model: Skills Are Loader Specifications, Not Prompts

A SKILL.md file is not a long prompt the agent reads all at once. It is a **loader specification** -- it
describes what content should enter the agent's context window, when, and at what token cost.

The text of your instructions matters. The structure that delivers them matters more.

Two skills with identical instructions but different architectures can behave completely differently
and cost 3x more context to run. Every authoring decision should be framed as:
**"Which level does this content belong at?"**

---

## The Three-Level Loading System

| Level | Content | When Loaded | Approximate Cost |
|-------|---------|-------------|-----------------|
| 1 | YAML frontmatter (`name` + `description`) | Every turn, always | ~100 tokens per skill |
| 2 | SKILL.md body | Only when agent decides skill applies | Proportional to body length |
| 3 | `references/` files and `scripts/` | Only when body explicitly points to them | References: pay to read; Scripts: only pay for output |

**Implication**: If you put content at Level 2 that only matters in some cases, you pay for it on every
invocation. If you put content at Level 3 (references or scripts), you only pay when the agent actually
needs it for that task.

The target architecture is a **lean spine** at Level 2 that routes to **deferred chapters** at Level 3.

---

## Before Writing Any Instructions: Validate the Architecture Plan

Before drafting the SKILL.md body, the agent should answer these questions:

1. What percentage of invocations will need each section of the instructions?
2. Which sections contain environment-specific or domain-specific detail that could live in a reference file?
3. Are there any repetitive, deterministic operations that could be moved into a script?
4. What is the estimated token cost of the Level 2 body? Is it under 500 lines?

If the answer to question 4 is no, restructure before writing prose -- do not pad into a
monolith and plan to trim later.

---

## Architecture Patterns

### Prefer a Spine + References Over a Monolith

**Wrong approach**: One SKILL.md with 1,200 lines covering every scenario, all loaded on every invocation.

**Right approach**: A 150-300 line SKILL.md spine that contains the core workflow and explicit pointers to
reference files for domain-specific, environment-specific, or rarely-needed detail.

Example structure for a complex skill:

```
my-skill/
├── SKILL.md              (spine: workflow, routing logic, gotchas -- under 500 lines)
└── references/
    ├── framework-a.md    (loaded only when task involves framework A)
    ├── framework-b.md    (loaded only when task involves framework B)
    └── schema-ref.md     (loaded only when agent needs schema detail)
```

The SKILL.md body should explicitly tell the agent when to read each reference file. For example:
"If the task involves framework A, read `references/framework-a.md` before proceeding."

### Use Scripts for Deterministic, Repetitive Operations

Scripts in `scripts/` are executable -- the agent runs them and receives only the output in context.
The script source code itself does not consume context tokens.

This is the right place for: file transformation, data extraction, metric calculation, any operation
where the logic is fixed and you want to pay only for results, not for re-reading instructions.

---

## Antipatterns: Check For These Before Finalizing

### Antipattern 1: Frontmatter on Reference Files

**What it is**: Adding YAML `name`/`description` frontmatter to files inside `references/`.

**Why it fails**: Frontmatter marks a file as a top-level skill visible at routing time. Reference files
with frontmatter get added to the agent's always-loaded skill list. The agent may trigger the reference
file directly -- without the parent skill body that gives those instructions their meaning -- producing
subtly wrong output that is hard to trace.

**Fix**: Reference files must have no frontmatter. They are chapters, not skills.

### Antipattern 2: Hardcoded Workspace Paths

**What it is**: Instructions that assume a specific directory structure. Example: "Navigate to `modules/web`
and run the build."

**Why it fails**: Works on the author's machine. Silently fails the moment the skill runs in any other
repo layout. The agent finds the wrong directory or no directory, produces output in the wrong place, and
may not error -- just wrong output.

**Fix**: Write instructions that tell the agent to **discover** the correct path rather than declare it.
- "Search for the build configuration file."
- "Identify the relevant module by finding its `package.json`."
- "Read the workspace structure before assuming any path."

The skill becomes more abstract but portable.

### Antipattern 3: No Gotchas Section

**What it is**: Omitting a dedicated section for environment-specific deviations from reasonable defaults.

**Why it fails**: The agent's default behavior is correct for the average environment. Your environment is
not average. Turborepo must run from the repo root. Your API uses a non-standard authentication header.
Your build has a required pre-step most projects don't have. None of this lives in the model's training.
The agent will silently do the reasonable-average thing, which is wrong for your setup.

**Fix**: Include a `## Gotchas` section. Each entry should be a single, direct instruction addressing one
specific deviation. Do not explain philosophy -- just state the constraint.

Example:
```
## Gotchas
- Always run `turbo build` from the repository root, never from inside a module directory.
  Running from inside a module causes cache misses and incorrect dependency resolution.
```

Treat the Gotchas section as the highest-maintenance section of any skill. It grows as the skill is used.

### Antipattern 4: No Evaluation Baseline

**What it is**: Building and shipping a skill without any measurable definition of what "working correctly"
means.

**Why it fails**: Model upgrades are silent regressions. A skill tuned on one model is calibrated to that
model's compliance characteristics. A more capable model may interpret instructions rather than follow
them -- pulling output toward its own aesthetic, its own conventions, the statistical center of its
training data. The author's voice or organization's conventions are not that center.

Without evals, there is no way to know:
- Which instructions are being over-applied
- How much output has drifted from the intended behavior
- Whether a model upgrade improved or degraded the skill

**Fix**: Before finalizing any skill, establish a Golden Set:
- 3-5 realistic prompts that represent the core use cases of the skill
- For each: run once with the skill, once without (paired baseline runs)
- For measurable skills: define at least a few scriptable assertions (output length, structure, required
  fields present, readability score, etc.)
- Store the Golden Set alongside the skill
- Re-run on every model change and every significant skill edit

The question is never "does this output look good?" It is "is this output better than the baseline,
and by how much?"

---

## Description Quality: The Most Important Field

The `description` frontmatter field is the **only thing the agent reads on every turn** to decide
whether this skill applies. If it is wrong, nothing else matters -- the skill will never trigger, or
will trigger in wrong contexts.

Requirements for a high-quality description:
- State clearly what the skill does
- State specifically when to use it (trigger contexts, user phrases, task types)
- Be slightly "pushy" -- explicitly enumerate the contexts where the skill should activate, because
  agents tend to undertrigger skills when descriptions are vague
- Do not bury "when to use" information inside the SKILL.md body -- all routing logic belongs in the
  description

After the skill is drafted and tested, run the description optimizer if available.

---

## Model Compliance Calibration Warning

When a skill encodes personal style, organizational conventions, or specific formatting constraints, be
aware that:

- A more capable model has stronger aesthetic priors
- Stronger priors mean the model is more likely to interpret instructions toward its own defaults
  rather than follow them literally
- "Write shorter sentences" may mean "apply judgment about when brevity serves the sentence" to one
  model and "hard cap every sentence at 7 words" to another

If a skill is style-sensitive, this requires:
1. Testing explicitly on the target model before shipping
2. Updating the Golden Set for the new model baseline when upgrading
3. Adding specificity to instructions where the model is known to over-interpret
   (e.g., instead of "write short sentences", say "aim for sentences under 20 words, but allow
   longer sentences when the clause structure requires it for clarity")

---

## Skill Creation Checklist

Use this before declaring a skill complete:

- [ ] SKILL.md body is under 500 lines; if longer, a spine+references structure is in place
- [ ] No frontmatter exists on any file inside `references/`
- [ ] No hardcoded workspace paths; all path-dependent instructions use discovery language
- [ ] A `## Gotchas` section exists and covers all known environment-specific deviations
- [ ] The `description` frontmatter accurately describes both what the skill does AND when to use it
- [ ] A Golden Set of 3-5 test prompts exists with paired baseline results
- [ ] At least a few scriptable assertions are defined for measurable outputs
- [ ] The skill has been tested on the specific model version that will run it in production
- [ ] Reference files are only loaded on demand, with explicit pointers in the SKILL.md body

---

## Quick Reference: What Goes Where

| Content Type | Level | Location |
|---|---|---|
| Skill name and trigger context | 1 | YAML frontmatter |
| Core workflow and sequence | 2 | SKILL.md body |
| Gotchas and environment constraints | 2 | SKILL.md body (dedicated section) |
| Routing logic to reference files | 2 | SKILL.md body |
| Domain-specific or rarely-needed detail | 3 | `references/*.md` |
| Deterministic operations with fixed logic | 3 | `scripts/` |
| Templates and static assets | 3 | `assets/` |
| Test prompts and baseline results | -- | `evals/` (alongside skill) |
