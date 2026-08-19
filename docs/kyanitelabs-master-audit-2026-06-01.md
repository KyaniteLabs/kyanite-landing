# KyaniteLabs Master Audit

Date: 2026-06-01

Scope: consolidated audit of visual design, typography, UI/UX, copywriting, conversion copy, Spanish language quality, public-surface hygiene, route leakage, and missed issues across the KyaniteLabs website.

Remediation plan: `docs/kyanitelabs-design-remediation-plan-2026-06-01.md`.

This document replaces the three separate working audits:

- `brand-unification-audit.md`
- `design-adversarial-audit-2026-06-01.md`
- `copywriting-audit-2026-06-01.md`
- `process-leak-audit-2026-06-01.md`

## BLUF

The strongest Kyanite direction is already visible: the generated project-image proof wall. It feels specific, technical, tactile, and non-default. That is the canon.

The main problem is that the rest of the site has not fully caught up. Shop, product pages, implementation, intake, blog, and some Spanish surfaces still feel more like support templates than the same high-taste Kyanite system.

The second problem is language. Kyanite has a good voice when it names concrete things: repos, MCP servers, commands, install paths, screenshots, tests, diagnostic reports, first runs, and handoff notes. It weakens when it repeats internal words like `implementation`, `tool`, `proof`, `surface`, `outcome`, `handoff`, and `usable`.

The third problem is public-surface hygiene. Some workspace/process boundaries are visible in production-like routes and copy. The clearest examples were the now-moved Tertulia prototype route, Cerafica API namespace exposure, internal org-structure wording, and the Spanish `Contactoo` bug.

## Status Since Audit

Completed in this pass:

- Tertulia client prototype files were moved out of `kyanite-landing` to the PuenteWorks client workspace.
- The public Flask route `/mockup/tertulia` was removed from Kyanite.

Still open:

- Cerafica API namespace is still present in Kyanite.
- Spanish `Contactoo` is still present until the duplicate replacement loop is fixed.
- Public copy still contains internal/process phrases.
- Secondary pages still need stronger propagation of the generated project-image visual system.

## Evidence Summary

Visual review:

- Desktop and mobile screenshots were taken across homepage, proof wall, shop, implementation, intake, about, blog, Spanish home, and mobile variants.
- The project image proof wall is the strongest visual surface.
- Secondary pages are cleaner than before but less distinctive.

Rendered copy sweep:

- 34 rendered routes were scanned for copy repetition.
- `implementation`: 174 matches
- `repo`: 164 matches
- `tool`: 143 matches
- `tools`: 109 matches
- `proof`: 97 matches
- `working`: 67 matches
- `usable`: 64 matches
- `surface`: 49 matches
- `handoff`: 48 matches
- `setup`: 51 matches
- `prompt`: 52 matches
- `prompts`: 50 matches

Process-leak sweep:

- 39 routes were scanned.
- No suspicious rendered HTML comments were found.
- Public-surface scanner found inside-baseball content ops language, Spanish typo leakage, unfinished/dev terms, internal/admin framing, agent/session residue, and generic CTA language.

## Canonical Design Direction

Keep:

- Generated project hero images as the primary visual language.
- Matte, dark, technical, machined surfaces.
- Cut-corner frames and source-map/grid texture.
- Cyan, amber, and magenta as sparse signal colors.
- Public proof before sales copy.
- Logo-bearing hero artwork on the homepage.
- Brand-specific project imagery for each open-source project.

Avoid:

- Fake glass.
- Pill buttons.
- Generic equal-card SaaS layouts.
- Purple-first AI styling.
- Text-only product shelves.
- Abstract phrases repeated without concrete artifacts.
- Process notes visible as product language.

## Durable Brand-Unification Findings

The earlier unification audit was directionally right: Kyanite should not feel like a generic AI agency, prompt shop, or soft SaaS consultancy.

Best durable brand spine:

> From weird workflow to usable AI tool.

Expanded:

> KyaniteLabs turns messy AI workflows, repos, and agent ideas into installable, explainable, public products.

Emotional register:

- corrupted lab signal resolving into a usable tool
- sharp crystalline tech, not bubbly startup AI
- public proof, not mystery consulting
- weird enough to be memorable
- disciplined enough to be trusted

Earlier drift that still matters:

- homepage, shop, implementation, intake, and product pages should not feel like separate brands
- the shop should not read as a generic prompt-pack shelf
- offer pages should not drift into sober generic consulting
- `mcp-video` should remain flagship proof because it connects public technical work, agentic media, and visible output
- video/social language should translate into the website as restrained texture and proof, not chaos

Updated interpretation:

The 2026-05-14 audit wanted the site unified around "weird workflow to usable AI tool." The 2026-06-01 audits refine that into a more concrete public promise:

> Inspect the repo. Bring the blocker. Leave with the path.

## Severity-Ranked Findings

### P0 - Cerafica API Namespace Is Exposed Inside Kyanite

Evidence:

- Route map includes many `/api/cerafica/*` endpoints.
- `/api/cerafica/health` returns `200` with health/config state.
- Disabled DB guard allows `/api/cerafica/health`.
- Content generation, order, waitlist, and checkout routes exist in the same Flask app.

Why it matters:

This mixes an adjacent product/client namespace into the Kyanite public runtime. Even if most routes are disabled now, the namespace creates public-surface confusion and future security risk.

Recommended fix:

1. Move Cerafica routes into a separate service/app.
2. If they must remain temporarily, return `404` for all `/api/cerafica/*` routes unless an explicit public flag is set.
3. Gate admin/content/order endpoints behind a token.
4. Remove config-state details from public health responses.
5. Add route-map tests that fail if unrelated brand namespaces are public in Kyanite production.

### P0 - Tertulia Prototype Was Publicly Exposed

Evidence:

- `/mockup/tertulia` previously returned a Tertulia With Saints prototype page.
- It was unrelated to Kyanite's public brand.

Status:

- Fixed in this pass by moving files to the PuenteWorks client workspace.
- Fixed in this pass by removing the Flask route.

Recommended follow-up:

- Add a route regression test that asserts `/mockup/tertulia` is `404`.

### P1 - Spanish UI Has Visible `Contactoo`

Evidence:

- Spanish nav and footer render `Contactoo`.
- Root cause is a duplicate replacement pass in `spanishify`.

Why it matters:

This visibly reveals brittle automated translation machinery. It is especially damaging because Kyanite sells localization and QA-adjacent credibility.

Recommended fix:

1. Remove the duplicate replacement loop.
2. Add a rendered Spanish smoke test asserting `Contactoo` is absent.
3. Add a small Spanish glossary test for critical nav labels.

### P1 - The Project Image System Is Strong, But Not Propagated

Evidence:

- Homepage proof cards use generated project images.
- Shop product cards are mostly text-only.
- Product detail pages are text-led.
- Implementation and intake pages are mostly cards/lists/forms without equivalent proof imagery.

Why it matters:

The new desired direction is not simply "dark technical cards." It is generated project-image proof as brand evidence. The homepage shows the right world. The commerce and service pages still feel like support pages.

Recommended fix:

Create a `visual_proof_asset` model for:

- products
- implementation offers
- blog clusters
- support surfaces
- intake/context packet visuals

### P1 - Page Template Drift

Evidence:

- Homepage nav uses one set of nouns.
- Implementation, product, and intake pages vary labels and CTA language.
- Product detail pages drop Proof.

Why it matters:

Users experience multiple dialects of the same product line.

Recommended nav contract:

- Tools
- Proof
- Notes
- Shop
- About
- Contact
- Get Help
- EN/ES

### P1 - Internal Business-Structure Copy Is Too Visible

Detected phrases:

- `legal/payment container`
- `technical/product line`
- `public proof surface`
- `Broader consulting belongs under PuenteWorks`

Why it matters:

The PuenteWorks/Kyanite relationship is real, but the current language reads like internal operating-model notes.

Recommended public wording:

> KyaniteLabs is a focused technical lab from PuenteWorks LLC. Kyanite handles public tools, operator assets, and implementation help tied to those tools.

Footer/legal wording:

> KyaniteLabs is operated by PuenteWorks LLC.

Avoid:

- legal/payment container
- technical/product line
- public proof surface
- belongs under

### P1 - Agent/Session Residue Is Visible In Copy

Detected phrases:

- `one-off chat`
- `strategy theater`
- `lead-gen theater`
- `messy truth`
- `messy process`
- `structured implementation request`
- `does not automatically buy, publish, or commit to anything`

Why it matters:

These phrases sound like internal workflow doctrine or an agent postmortem. Some have good attitude, but they pull visitors behind the curtain.

Replacement direction:

- `one-off chat` -> `a call no one can repeat`
- `strategy theater` -> `vague advice`
- `lead-gen theater` -> `generic sales calls`
- `messy truth` -> `the real setup`
- `messy process` -> `the work behind the proof`
- `structured implementation request` -> `implementation brief`

### P1 - Touch Targets Need Another Pass

Evidence:

- Several global nav/footer/mobile targets are likely below the 44px guideline.

Why it matters:

Small links can make an otherwise premium interface feel fussy.

Recommended fix:

- Normalize nav and footer tap targets.
- Keep visual density, but enlarge the interactive box.
- Verify mobile screenshots after changes.

## Copywriting Findings

### Core Voice

The best Kyanite voice is:

- technically literate
- allergic to vague AI hype
- practical
- proof-first
- builder-to-builder
- dry without being cold
- commercial without feeling SaaS-generic

Strong existing lines:

- "Proof you can inspect before asking for help."
- "The thinking should make the tool easier to trust."
- "Make the useful thing usable."
- "Not courses. Not vague prompt dumps."
- "Kyanite already builds the proof."
- "Designed as workflows, not prompt confetti."

### Weak Pattern

The site sometimes explains itself through internal nouns:

- implementation
- surface
- handoff
- outcome
- tool
- usable
- proof

These words are useful, but they are overburdened. Public copy needs more concrete nouns:

- repo
- command
- config
- install path
- first run
- example
- handoff note
- build note
- diagnostic
- proof role
- source link
- context packet

### Positioning

Current implicit positioning:

> Open-source proof. Paid help to reach the result faster.

Keep it as the backbone.

Sharper versions:

> Public AI tools, made runnable in real environments.

> Inspect the repo. Bring the blocker. Leave with the path.

> From public repo to usable AI workflow.

### Homepage Copy

Recommended hero:

Eyebrow:

> Implementation help for public AI tools

Hero line:

> Turn public repos into working AI systems.

Lead:

> Bring the Kyanite repo, MCP server, media pipeline, localization pass, or diagnostic you want running. Kyanite helps install it, adapt it to your setup, document the tradeoffs, and leave you with commands you can use again.

Primary CTA:

> Get a Tool Working

Secondary CTA:

> Inspect the Public Proof

### Homepage Proof Section

Keep:

> Proof you can inspect before asking for help.

Recommended supporting copy:

> Each project card links to a public artifact: repo, language, update date, proof role, and the kind of blocker it can help solve.

### Homepage Outcome Model

Keep:

> Make the useful thing usable.

Recommended body:

> Kyanite starts with a real delay, risk, or confusing workflow. Then it turns the fix into a repo, MCP server, CLI, QA pass, guide, or product people can inspect before they ask for help.

### Implementation Page

Current idea is strong:

> Get the tool working without doing every setup step alone.

Recommended lead:

> Bring a Kyanite repo, MCP server, media pipeline, localization QA pass, or diagnostic that should work but does not yet work in your environment. You get setup help, adaptation notes, tradeoffs, and a handoff you can repeat.

Primary CTA:

> Send the Implementation Brief

Secondary CTA:

> Email the Context

### Intake Page

Recommended H1:

> Send the blocker before buying anything.

Alternative:

> Tell Kyanite what should work, and where it breaks.

Recommended lead:

> This form is the first filter. Send the repo, setup, blocker, and success condition. Kyanite will review the context and reply with the best next step if the request fits the lab.

Recommended submit:

> Send the Implementation Brief

### Shop Page

Recommended H1:

> Operator assets for people building with agents.

Recommended body:

> Claude Code structures, prompt systems, hooks, workflow recipes, and implementation templates you can adapt in one sitting. Not courses. Not vague prompt dumps. Small artifacts for people already shipping with agents.

CTA:

> See What's Inside

### Product Detail Pages

Recommended structure:

- What you get
- Who this is for
- What is inside
- How to use it
- Not for
- Buyer questions

Recommended CTA:

> Buy the Download on Ko-fi

### Blog Page

Keep:

> Published lab notes only.

Recommended lead:

> Kyanite publishes after there is a build, lesson, product decision, or workflow worth inspecting. The notes cover open-source AI tools, MCP systems, agentic media, developer learning, implementation, and the work behind the proof.

### Blog Post CTA

Recommended:

> Want this working in your environment?

Body:

> Send the repo, setup, and blocker. If the request fits Kyanite's tools or build practice, the paid path can cover setup, adaptation, docs, examples, or a handoff you can repeat.

## Spanish Copy Findings

Critical:

- Fix `Contactoo`.

Strategic:

- Spanish needs a deliberate bilingual glossary, not raw string replacement.
- Some English terms can stay, but only as a style choice.

Suggested glossary:

- setup -> instalacion, except when referring to a technical setup object
- handoff -> entrega, traspaso, or handoff only as a named Kyanite concept
- build -> build for builder culture, construccion for process
- fit -> encaje, or fit only in short product language
- checks -> verificaciones
- pipeline -> pipeline if technical, flujo if general
- implementation -> implementacion
- proof -> prueba or evidencia by context

Recommended Spanish hero:

> Convierte repos publicos en sistemas de IA que corren.

Lead:

> Trae el repo, servidor MCP, pipeline de medios, QA de localizacion o diagnostico que quieres hacer funcionar. Kyanite ayuda a instalarlo, adaptarlo a tu entorno, documentar los tradeoffs y dejarte comandos que puedas repetir.

## Visual System Findings

### Project Image As Primitive

Missing design-system primitive:

> project image / proof asset / generated artifact visual

This should be reusable across:

- proof cards
- shop products
- blog cards
- implementation pages
- intake context panels
- open-source project pages if added later

### Product and Shop Visuals

Current shop cards sell from text. They need product-specific visual proof panels.

Recommended:

- generated product-cover images
- artifact preview snippets
- "inside the download" screenshots
- small proof badges tied to real deliverables

### Implementation Visuals

Implementation should show a tangible process artifact:

- blocked repo
- install trace
- config/command path
- handoff note
- result checkpoint

This should not become generic workflow illustration. It should look like Kyanite evidence.

### Blog Visuals

Blog index is editorially solid but visually behind the proof wall.

Recommended:

- image-led lab note cards
- generated editorial covers by topic cluster
- less reliance on plain text-card stacks

### Typography

Typography is good but not fully role-systematized.

Recommended modes:

- hero/brand mode
- proof/card mode
- editorial/blog mode
- commerce/product mode
- form/intake mode
- Spanish long-string mode

Web font loading is good enough, but not elite. Add a stronger preload/font-display strategy only after layout and copy are stabilized.

## Public-Surface Hygiene Findings

### AI/GEO Language In Human Copy

Terms like `metadata`, `AI-readable discovery layer`, `JSON-LD`, and `sitemap` are appropriate in the SEO/GEO blog post and machine-readable files. They feel wrong in homepage product claims.

Recommended homepage wording:

> Package the repo with examples, screenshots, tests, docs, and a clear first-run path so someone can judge the work without guessing.

### AI Context Files Need A Tone Filter

`llms.txt` and `llms-full.txt` are public. AI assistants may quote them directly.

Replace:

- empty lead-gen theater
- legal/payment container
- public proof surface

Recommended:

> KyaniteLabs is a PuenteWorks LLC technical lab for public AI tools, operator assets, and implementation help. It is best for people who want a Kyanite repo, MCP server, media pipeline, localization QA pass, or diagnostic working in a real environment.

### Admin Routes

Good:

- `/api/sales/stats` and `/api/waitlist` fail closed when `ADMIN_API_TOKEN` is absent.

Concern:

- Admin path protection is path-list based and easy to regress.

Recommended:

- Add public-route audit tests.
- Prefer one protected admin blueprint.

### Privacy Policy Scope

Privacy copy mentions posting workflow data, connected account identifiers, access tokens, refresh tokens, captions, and publishing status.

This may be accurate if Kyanite has a visible posting workflow. If not, it reads like another app's privacy policy leaked in.

Recommended:

- Split privacy sections by product area.
- Remove or contextualize unrelated data categories.

## Copy and CTA Matrix

Recommended CTAs:

- Homepage primary: `Get a Tool Working`
- Homepage secondary: `Inspect the Public Proof`
- Proof cards: `Open Repo`
- Blog page: `Read the Notes`
- Blog post service CTA: `Send the Implementation Brief`
- Shop card: `See What's Inside`
- Product detail: `Buy the Download on Ko-fi`
- Intake submit: `Send the Implementation Brief`
- Contact form: `Send the Context`

Avoid:

- Learn more
- View details
- Submit
- Start intake
- Get started

## Page Role Map

Homepage:

- Job: orient and route.
- Copy mode: clear, proof-first, commercial enough.
- Visual mode: brand hero plus proof wall.

Proof/projects:

- Job: build trust.
- Copy mode: concrete and artifact-based.
- Visual mode: generated project proof assets.

Implementation:

- Job: make paid help understandable.
- Copy mode: service clarity, boundaries, deliverables.
- Visual mode: setup trace / handoff artifact.

Intake:

- Job: reduce anxiety and collect useful context.
- Copy mode: calm, specific, procedural.
- Visual mode: context packet, not generic form page.

Shop:

- Job: sell small artifacts.
- Copy mode: practical and preview-oriented.
- Visual mode: product artifact covers.

Product details:

- Job: remove purchase uncertainty.
- Copy mode: deliverable, who-for, not-for, how-to-use.
- Visual mode: preview, contents, proof.

Blog:

- Job: prove thinking and route interested readers.
- Copy mode: technical, opinionated, less promotional.
- Visual mode: editorial artifact covers.

About:

- Job: founder credibility and taste.
- Copy mode: story plus standard.
- Visual mode: lab/founder proof, not generic bio.

## Design-System Updates Needed

Add tokens/components for:

- proof asset frame
- project image card
- product artifact cover
- implementation trace panel
- intake context packet
- editorial/blog cover
- Spanish long-label rules
- shared nav contract
- tap-target sizing
- CTA role matrix

Retire or reduce:

- obsolete hero-era selectors
- text-only commerce cards
- internal/process wording in public templates
- duplicated page-local nav patterns

## Regression Tests To Add

Public route tests:

- `/mockup/tertulia` is `404`.
- `/api/cerafica/health` is not public in Kyanite production mode, unless explicitly enabled.
- unauthenticated `/api/sales/stats` is `404`.
- unauthenticated `/api/waitlist` is `404`.

Spanish tests:

- rendered Spanish routes do not contain `Contactoo`.
- critical nav labels match the glossary.

Public copy tests:

- rendered public pages do not contain:
  - `legal/payment container`
  - `public proof surface`
  - `empty lead-gen theater`
  - `strategy theater`
  - `one-off chat`
  - `structured implementation request`

Visual QA:

- desktop homepage
- desktop proof wall
- desktop shop
- desktop product page
- desktop implementation
- desktop intake
- desktop blog
- Spanish homepage
- mobile homepage
- mobile shop
- mobile intake

## Highest-Leverage Work Order

1. Fix Spanish `Contactoo` and add a regression test.
2. Keep Tertulia outside Kyanite and verify `/mockup/tertulia` is gone.
3. Decide Cerafica boundary: separate service or fully gated namespace.
4. Replace internal/process phrases across homepage, implementation, blog post CTA, and `llms.txt`.
5. Rewrite homepage hero/lead/CTAs around repo, blocker, commands, and first run.
6. Rewrite implementation lead so visitor outcome comes before legal/business framing.
7. Replace generic CTAs like `View details` and `Start intake`.
8. Add product page sections: who for, not for, what is inside, how to use it.
9. Add product and blog generated images that match the proof-wall direction.
10. Normalize shared nav and touch targets across templates.
11. Remove old dead product-state markup if unused.
12. Add a route-map/public-surface test so this class of issue does not return.

## If Only One Thing Gets Done

Make the project-image proof system the site-wide primitive and remove public process leakage around it.

The brand is strongest when it says:

> Here is the public artifact. Here is what it proves. Bring the blocker if you want it working in your environment.
