{"name":"architecture-overview-spec","origin":"github.com/lago-morph/ai-skills","content_hash":"6009b61f4a659cdad0c79abbfa678a5156b5da0a631517f0dd98d88a296bde1c","version":"0.1.0","state":"live","implemented_as":null,"merged_into":null}
# architecture-overview-spec

A reusable structure for producing a comprehensive architecture overview document for a software platform. Apply when asked to write or revise an architecture document that needs to serve as a starting point for new technical readers and a reference for ongoing decision-making.

## When to use

- The user asks for an architecture overview, architecture document, or "starting point for technical readers."
- The system being described is a multi-component platform (not a single application or service).
- The document needs to serve as a reference that's read repeatedly, not a one-shot proposal.
- There is real ambiguity about boundaries between install / configure / custom-build work, and that needs to be explicit.

## Section structure

Use these sections in this order. Skip sections only when the user explicitly says they don't apply.

1. **Purpose of this document** — one paragraph: who reads it, what they get from it.
2. **Goals** — bulleted list of what the platform exists to do. Include scale targets and explicit non-goals.
3. **Baseline assumptions** — what's already in place that we build on top of. Table format: Component | Role | How the platform uses it. Explicit about what is *not* baseline.
4. **High-level architecture** — one diagram showing major planes/tiers (Users, Interfaces, Control/Gateway, Workloads/Data, Platform Services, etc.) with brief prose describing each plane.
5. **Software added to baseline** — table classifying every new component by activity type: **install** (Helm + Helm values), **configuration** (declarative settings, YAML, no code), **custom development** (writing code, even if marketed as "plugins" or "compositions"). Include a callout for things that look like configuration but are really custom development (Rego policies, plugin code, composition functions).
6. **Architectural views** — subsystem-level architecture, one subsection per major concern. Each subsection has a diagram and supporting prose. Typical concerns: gateway, runtime, memory/data, knowledge base, observability, security/policy, eventing, capability registries, multi-tenancy, self-management.
7. **Use cases** — each use case gets **two diagrams**: an architecture view (which components participate, how they connect) followed by a sequence view (how interactions flow over time). Pairing both is essential — the architecture diagram alone hides timing; the sequence diagram alone hides structure.
8. **CI/CD integration requirements** — what the platform expects from CI; what CI is responsible for; required CI capabilities. Be explicit about which CI systems are in scope vs out of scope, and per-version.
9. **OSS limitations and required custom development** — table with columns: Tool | OSS limitation | Fill-in we build. This makes it concrete that adopting OSS is not free; specific development is required to fill specific gaps.
10. **Documentation plan** — Diataxis four modes (tutorials, how-tos, reference, explanation), plus per-product architecture-specific docs, operator runbooks, maintainer/extender docs for custom code, docs-on-docs.
11. **Dashboards** — operator (cross-cutting / integrated) and developer (analysis / optimization) categories.
12. **Training** — operator and developer tracks, with concrete module lists.
13. **Testing framework** — what layers exist (unit / integration / end-to-end / UI), what tools per layer, how they're orchestrated.
14. **Components and dependencies** — workstream breakdown. Each workstream is a coherent grouping. Each component has standard deliverables. Include a dependency graph (Mermaid flowchart).
15. **Glossary** — terms with special meaning in this architecture. Place at the end so the document reads top-to-bottom while remaining a lookup reference.

## Diagram conventions

- Use **Mermaid** for diagrams. They render in any markdown viewer that supports Mermaid (GitHub, MkDocs, GitLab, many others).
- For architecture views, use `flowchart` or `flowchart LR/TB`.
- For sequences, use `sequenceDiagram` with `autonumber`.
- For each use case in section 7, **always include both** an architecture diagram AND a sequence diagram. This is non-negotiable; one without the other leaves a real gap.
- Keep diagrams readable — if a diagram has more than ~25 nodes, split it.

## Software-added table conventions

Three activity types only: **install**, **configuration**, **custom development**. A single component can have multiple types (e.g., "Install (Helm) + custom Python callbacks").

When something nominally looks like configuration but is really custom development (Rego policies, OPA bundles, frontend plugins, composition functions, controller code), say so explicitly. Add a callout under the table listing these — they're the landmines.

## OSS limitations table conventions

For each commercial gap in an OSS tool we adopt, include a row. Columns:

- **Tool**: which OSS component
- **OSS limitation**: what the free version doesn't have (SSO, audit, RBAC, etc.)
- **Fill-in we build**: how we work around it (auth proxy, callback, plugin, glue service, etc.)

The cumulative table is the single best argument for the size of the custom-development workstream.

## Component breakdown conventions

Group components into **workstreams**. Common workstreams: install/operate vendor components, custom platform development, documentation, dashboards, training, production readiness.

Define **standard deliverables** that apply to every component in a workstream — typically including: per-product docs, runbooks, tests at multiple layers, dashboards, observability hooks, plugin where applicable, contribution to any cross-component services (e.g., diagnostic agent toolset), tutorial / how-to.

Include a **dependency graph** as a Mermaid flowchart showing which components depend on which. This is the document users return to when planning sequencing.

## Format and style

- Prose first, lists when content is naturally enumerated, tables when content has structure.
- Keep paragraphs reasonably short.
- Each section is self-contained enough that a reader can land on it via search and get value without reading from the start.
- Cross-reference other sections by number, not just by name (e.g., "see section 6.3").
- Use **bold** for emphasis sparingly; use it for terms being defined and for genuinely critical points.
- Use callout blockquotes for warnings, especially "this looks easier than it is" notes.

## What this spec does NOT cover

- Project management or implementation planning beyond the component breakdown.
- Detailed design of any individual component (those go in design specs).
- ADRs (those are separate documents capturing single decisions with full reasoning).
- The parallel decision-tracking document — see `architecture-backlog-spec.md`.

## Common pitfalls

- **Skipping the use-case sequence diagrams.** Without them, time-ordered behavior is invisible.
- **Soft-pedaling custom development.** OSS components rarely come without gaps; pretending they do leads to schedule miss when reality lands.
- **Forgetting the glossary.** Special-meaning terms ("Platform Agent", "CapabilitySet", "approved peer") drift if not defined once and referenced.
- **Letting the document become a backlog.** When deferred decisions accumulate in the architecture document, it loses authority. Move them to the parallel backlog.
- **Forgetting cross-cutting deliverables on each component.** Without standard deliverables in the workstream definition, individual components ship inconsistently.
