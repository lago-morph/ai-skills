---
name: codex-skill-creator
description: Create, update, evaluate, package, and optimize Codex skills. Use when the user wants to make a new skill, merge or port an existing skill into Codex, improve skill triggering, add agents/openai.yaml metadata, create bundled scripts/references/assets, validate a skill package, or run practical evals and benchmark comparisons for a skill.
metadata:
  short-description: Create and evaluate Codex skills
---

# Codex Skill Creator

Use this skill to create new Codex skills and improve existing ones. A good skill is a compact, self-contained package that gives Codex specialized workflow knowledge, references, scripts, and assets without loading unnecessary context by default.

## Core Workflow

1. Capture the user's intent and the concrete tasks the skill should support.
2. Decide what belongs in `SKILL.md` and what should move into bundled resources.
3. Create or update the skill package.
4. Validate metadata and links.
5. Test on realistic prompts, compare outputs when useful, and iterate.
6. Package or summarize the final result.

Adapt the amount of process to the request. For a small wording fix, edit and validate. For a new or high-impact skill, draft examples, build resources, run evals, and iterate with the user.

## Communicating With The User

Match the user's level of detail. Briefly explain terms like "eval", "assertion", and "frontmatter" when the user has not signaled familiarity.

Avoid forcing a formal benchmark loop on subjective or exploratory work. Offer it when objective comparison matters, such as file transforms, extraction tasks, generated artifacts with clear requirements, or trigger-description tuning.

## Skill Anatomy

Every skill has:

```text
skill-name/
├── SKILL.md
│   ├── YAML frontmatter with name and description
│   └── Markdown instructions
├── agents/
│   └── openai.yaml
└── bundled resources, as needed
    ├── scripts/
    ├── references/
    └── assets/
```

### Frontmatter

Use:

```yaml
---
name: my-skill
description: What the skill does and the specific situations where Codex should use it.
---
```

The `description` is the primary trigger surface. Put "when to use this skill" details in the description because Codex sees the description before loading the body. Keep it specific enough to distinguish neighboring skills.

### agents/openai.yaml

Create or maintain `agents/openai.yaml` for Codex UI metadata. Read `references/openai_yaml.md` before generating or changing it.

Required practical fields:

```yaml
interface:
  display_name: "Human Name"
  short_description: "25 to 64 character UI blurb"
  default_prompt: "Use $my-skill to ..."
```

Optional fields include icons, brand color, dependencies, and `policy.allow_implicit_invocation`.

Use `scripts/generate_openai_yaml.py` to generate deterministic metadata:

```bash
python3 scripts/generate_openai_yaml.py <path/to/skill-folder> \
  --interface display_name="My Skill" \
  --interface short_description="Do the thing well" \
  --interface default_prompt="Use $my-skill to handle this workflow."
```

### Bundled Resources

Use bundled resources when they reduce repeated work or keep `SKILL.md` lean.

- `scripts/`: deterministic or repetitive operations, validators, converters, packagers, or helpers.
- `references/`: detailed documentation, schemas, policies, examples, or variant-specific guidance that should be loaded only when needed.
- `assets/`: templates, icons, fonts, boilerplate, sample files, or other resources used in outputs.

Do not add extra files such as `README.md`, install guides, changelogs, or unrelated notes unless the user explicitly needs them. A skill package should contain only files that help Codex perform the skill.

## Progressive Disclosure

Keep the default load small:

1. Metadata is always visible.
2. `SKILL.md` loads only when the skill triggers.
3. References, scripts, and assets are loaded or executed only when relevant.

Put only the core workflow and routing guidance in `SKILL.md`. Move large details into references, and link them clearly from `SKILL.md` with "read this when..." guidance.

For multiple domains or providers, split by variant:

```text
cloud-deploy/
├── SKILL.md
└── references/
    ├── aws.md
    ├── azure.md
    └── gcp.md
```

## Creating A Skill

### Capture Intent

Extract answers from the conversation before asking questions. Fill these gaps:

1. What should this skill enable Codex to do?
2. What user requests should trigger it?
3. What outputs should it produce?
4. What examples, files, APIs, schemas, policies, or templates define success?
5. Should we run test prompts or is a direct edit enough?

Ask only the next necessary question. If the user does not specify a path, create installable skills under `${CODEX_HOME:-$HOME/.codex}/skills`.

### Plan Reusable Contents

For each concrete example, ask:

1. What would Codex otherwise need to rediscover or rewrite?
2. Would a script, reference, or asset make repeated use more reliable?
3. What details must stay in `SKILL.md` so Codex can route correctly?
4. What details can be loaded only when the task needs them?

### Initialize

For new skills, use the initializer unless there is a good reason to hand-create files:

```bash
python3 scripts/init_skill.py <skill-name> --path "${CODEX_HOME:-$HOME/.codex}/skills"
python3 scripts/init_skill.py <skill-name> --path "${CODEX_HOME:-$HOME/.codex}/skills" --resources scripts,references
```

The initializer creates a skill directory, `SKILL.md`, optional resource directories, and `agents/openai.yaml`.

### Edit

Write for another Codex instance. Include procedural knowledge that is non-obvious, reusable, and tied to the skill's purpose.

Prefer:

- imperative instructions
- compact examples
- explicit output formats when required
- links to references with conditions for when to read them
- scripts for fragile or repeated operations

Avoid:

- broad background that Codex likely already knows
- hidden "when to use" sections in the body
- unexplained hard rules
- overfitting to one test case
- product-specific assumptions that do not match Codex

## Validation

Run the quick validator:

```bash
python3 scripts/quick_validate.py <path/to/skill-folder>
```

Also check:

```bash
find <path/to/skill-folder> -maxdepth 4 -type f | sort
rg -n 'TODO|FIXME|legacy|deprecated|placeholder|product-specific' <path/to/skill-folder>
```

Resolve stale placeholders, broken links, and product-specific references before considering the skill done.

## Test Cases

For substantial new skills or risky edits, create 2 to 3 realistic prompts. Use the kind of prompt a user would actually type, with enough detail to exercise the skill.

Save prompts in `evals/evals.json` when you are running a formal evaluation:

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "User's task prompt",
      "expected_output": "Description of expected result",
      "files": []
    }
  ]
}
```

Read `references/schemas.md` for the complete schema.

## Running Evaluations In Codex

Codex may have subagents available, but use them only when the user explicitly asks for delegation, parallel agents, or independent agent evaluation. If subagents are not explicitly authorized, run tests locally or explain what would be tested.

Put results in `<skill-name>-workspace/` as a sibling to the skill directory. Organize by iteration:

```text
<skill-name>-workspace/
└── iteration-1/
    └── eval-descriptive-name/
        ├── with_skill/
        │   └── outputs/
        └── baseline/
            └── outputs/
```

### With Skill

Run the task while explicitly using the skill:

```text
Use the skill at <path-to-skill> to complete this task:
<eval prompt>

Input files: <files or none>
Save outputs to: <workspace>/iteration-N/<eval-name>/with_skill/outputs/
```

### Baseline

Use a baseline when it adds value:

- New skill: run the same prompt without the skill.
- Existing skill: compare against a snapshot of the original version.
- Small edits: skip baseline if the overhead is not worth it.

### Metadata And Timing

For each eval, write `eval_metadata.json`:

```json
{
  "eval_id": 0,
  "eval_name": "descriptive-name",
  "prompt": "The user's task prompt",
  "assertions": []
}
```

If timing and token information are available from the environment, save them to `timing.json`. If they are unavailable, omit the file rather than inventing data.

### Assertions And Grading

Draft objective assertions only when they can be checked reliably. Good assertions are specific, user-visible, and discriminating.

For programmatically checkable outputs, write a small checker script instead of eyeballing. For subjective outputs, use qualitative review.

When grading with the bundled grader guidance, read `agents/grader.md` and save `grading.json` in each run directory. Use the fields `text`, `passed`, and `evidence` exactly; the viewer expects that schema.

### Aggregate And Review

Run:

```bash
python3 -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <name>
```

Generate a static review artifact in headless Codex sessions:

```bash
python3 <codex-skill-creator-path>/eval-viewer/generate_review.py \
  <workspace>/iteration-N \
  --skill-name "my-skill" \
  --benchmark <workspace>/iteration-N/benchmark.json \
  --static <workspace>/iteration-N/review.html
```

For iteration 2 and later, also pass `--previous-workspace <workspace>/iteration-<N-1>`.

Give the user the path to the generated HTML. If an interactive local browser is actually available and approved, the viewer can also run as a local server.

## Improving A Skill

Use feedback and eval results to improve general behavior, not just the specific examples.

Look for:

- repeated work that should become a bundled script
- long reference material that should move out of `SKILL.md`
- missing routing guidance in the description
- assertions that pass for both baseline and with-skill runs
- high variance or flaky evals
- instructions that cause wasteful tool use

After editing, rerun the relevant tests into a new iteration directory and regenerate the review artifact when useful.

## Advanced Comparison

For rigorous A/B comparison, read:

- `agents/comparator.md` for blind output comparison
- `agents/analyzer.md` for analyzing why one version won
- `agents/grader.md` for assertion grading

Use independent agents only when the user has explicitly authorized subagent or parallel agent work. Otherwise, perform a local comparison and label it as non-blind.

## Trigger Description Optimization

Skill triggering depends primarily on the `name` and `description` visible before the body loads. Optimize the description after the skill's behavior is otherwise in good shape.

Create a trigger eval set with realistic should-trigger and should-not-trigger prompts:

```json
[
  {"query": "the user prompt", "should_trigger": true},
  {"query": "near miss that should not trigger", "should_trigger": false}
]
```

Good eval prompts are concrete and task-like. Avoid negatives that are obviously unrelated; use near misses that test whether the description distinguishes adjacent skills.

The inherited `scripts/run_eval.py`, `scripts/improve_description.py`, and `scripts/run_loop.py` are Codex-oriented stubs in this merged skill. Use them only after confirming the local environment supports the needed model invocation path. If they cannot run in the current environment, manually inspect the eval set and improve the description based on likely trigger behavior.

## Packaging

Package a completed skill with:

```bash
python3 -m scripts.package_skill <path/to/skill-folder>
```

Preserve the original skill name when updating an existing skill. If the installed source is read-only, copy it to a writable work area, edit there, validate, then package or install the result.

## Reference Files

- `references/openai_yaml.md`: Codex UI metadata fields and constraints.
- `references/schemas.md`: JSON structures for evals, grading, timing, benchmarks, and review artifacts.
- `agents/grader.md`: How to evaluate assertions against outputs.
- `agents/comparator.md`: How to run blind comparisons when independent agents are authorized.
- `agents/analyzer.md`: How to analyze benchmark and comparison results.

## Final Checklist

Before finishing:

1. Validate `SKILL.md`.
2. Confirm `agents/openai.yaml` exists and matches the skill.
3. Search for stale product-specific references and placeholders.
4. Confirm scripts use `python3` in user-facing examples.
5. Verify any new scripts execute or explain why they were not run.
6. Summarize changed files and remaining risks.
