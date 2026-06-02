# KyaniteLabs Design Remediation Plan

Date: 2026-06-01

Goal: bring `kyanitelabs.tech` to the strongest possible visual, copy, UX, motion, and public-surface standard while preserving the new project-image direction as the design canon.

Source of truth: `docs/kyanitelabs-master-audit-2026-06-01.md`.

Specific user requests folded into this plan:

- Add animation/movement, but keep it tasteful and non-overwhelming.
- Replace the current grid/noise/source-map texture language with a Voronoi-inspired crystalline texture system.
- Preserve the generated project images as the desired visual direction.
- Keep pill buttons banned.
- Avoid fake glass.
- Typography changes, if any are required, must go through the web typography tool.

## BLUF

The best future version of Kyanite should feel like this:

> A dark crystalline technical lab where public tools become inspectable, runnable systems.

The site should not feel like a SaaS template, a prompt-pack shop, a consulting brochure, or an AI-generated dark landing page. It should feel like a specific world: matte black technical surfaces, Kyanite crystal geometry, public proof cards, generated project imagery, precise motion, and copy that names the actual artifact.

The remediation needs to happen in this order:

1. Stop public-surface leakage.
2. Stabilize one design system.
3. Replace grid/noise textures with a Voronoi crystalline material language.
4. Add restrained motion as a system, not one-off sparkle.
5. Propagate generated proof imagery through shop, product, implementation, intake, and blog.
6. Rewrite public copy around repo, blocker, command, first run, and handoff artifact.
7. QA across desktop, mobile, Spanish, reduced motion, accessibility, SEO/GEO, and route hygiene.

## North Star

Use this as the working brand line:

> Inspect the repo. Bring the blocker. Leave with the path.

Use this as the visual principle:

> Public proof, cut from dark crystalline material.

Use this as the interaction principle:

> Motion should make the surface feel alive and precise, never decorative or restless.

## Non-Negotiables

- No pill buttons.
- No fake glassmorphism.
- No generic AI purple/blue glow.
- No decorative orbs, bokeh, or lava-lamp mesh backgrounds.
- No text-only product shelves.
- No unrelated client/prospect routes inside Kyanite.
- No visible process wording like `legal/payment container`, `public proof surface`, `one-off chat`, or `strategy theater`.
- No animation without `prefers-reduced-motion`.
- No `transition: all`.
- No motion that animates `top`, `left`, `width`, or `height`.
- No generated texture that makes text harder to read.

## Desired Motion Level

Target motion intensity: 4.5/10.

This means:

- noticeable enough to feel intentional
- quiet enough to read the site without distraction
- mostly scroll-triggered, hover-triggered, or slow ambient
- no constant large movement
- no gimmick cursor trails
- no scroll hijacking

Allowed motion:

- fade/translate reveal on first viewport entry
- subtle stagger on project cards, blog cards, and product rows
- restrained hover depth on proof cards
- gentle Voronoi field drift in hero backgrounds
- small signal-line sweep on proof/hero plates
- mobile menu stagger reveal
- button active press feedback
- form status transitions

Avoid:

- parallax heavy enough to feel slippery
- typewriter loops on main copy
- infinite carousel unless it is isolated and slow
- looping card motion on all cards
- animated background behind long reading copy
- anything that competes with project images

## Voronoi Texture Direction

The current texture language still contains grid/noise/source-map energy. The next pass should replace that with a Voronoi-inspired crystalline system.

The Voronoi pattern should feel like:

- kyanite cleavage planes
- lab-map cells
- fractured mineral topology
- system boundaries
- proof artifacts held in a dark technical substrate

It should not feel like:

- generic science wallpaper
- frosted glass
- a gaming HUD grid
- noisy generative art
- decorative cyberpunk texture

### Texture Set

Create three texture assets:

1. `kyanite-voronoi-field`
   - global page material
   - very low contrast
   - large cells, slow visual rhythm
   - used on `body::before` or one fixed background pseudo-layer

2. `kyanite-voronoi-slab`
   - hero/page-hero material
   - stronger directional cells
   - should pair with logo hero image and product proof panels

3. `kyanite-voronoi-proof`
   - proof cards, product cards, implementation traces
   - higher local detail but still low contrast behind text

Preferred formats:

- SVG if the asset is geometric, small, and crisp.
- WebP/PNG if generated as painterly/matte material.

Performance constraints:

- Keep each asset light.
- Use fixed or section pseudo-elements, not repeated heavy backgrounds on every scrolling child.
- Animate only `transform` and `opacity`.
- Disable or freeze ambient motion under `prefers-reduced-motion`.

### CSS Replacement Targets

Replace grid/source-map texture usage in:

- `body::after`
- `.hero::before`
- `.hero-logo-stage::before`
- `.project-card::before`
- `.band`
- `.page-hero`
- proof/product card pseudo-elements

Do not remove CSS Grid layout. Only remove decorative grid-line background language.

### Voronoi Motion

Use one slow ambient movement only:

- `transform: translate3d(...) scale(...)`
- duration: 36s to 60s
- opacity range: subtle
- no animated blur
- no hue-rotate loops

Recommended pattern:

> A fixed Voronoi field drifts almost imperceptibly while section-specific Voronoi slabs remain static.

This gives life without noise.

## Remediation Phases

### Phase 0 - Public Surface Lockdown

Goal: stop all public trust leaks before polishing design.

Tasks:

- Keep Tertulia outside Kyanite under `PUENTEWORKS/clients/tertulia-with-saints`.
- Keep `/mockup/tertulia` removed.
- Decide the Cerafica boundary:
  - best: move Cerafica into its own service/app
  - acceptable short-term: return `404` for all `/api/cerafica/*` unless an explicit production flag enables it
- Fix Spanish `Contactoo`.
- Add route tests:
  - `/mockup/tertulia` is `404`
  - `/api/cerafica/health` is not public in Kyanite production mode
  - unauthenticated admin endpoints fail closed
- Add public copy scanner for banned process phrases.

Acceptance:

- no unrelated client/prospect pages render from Kyanite
- no Spanish route contains `Contactoo`
- no public page contains the highest-risk process-leak phrases
- smoke tests pass

### Phase 1 - Design-System Consolidation

Goal: one design system, not accumulated CSS eras.

Tasks:

- Collapse late CSS overrides into named sections:
  - tokens
  - base
  - layout
  - nav
  - hero
  - proof assets
  - cards
  - forms
  - motion
  - responsive
- Remove obsolete hero-era selectors and dead styles.
- Make one shared nav contract:
  - Tools
  - Proof
  - Notes
  - Shop
  - About
  - Contact
  - Get Help
  - EN/ES
- Normalize footer language and remove internal org-structure phrasing.
- Create reusable component classes:
  - `.proof-asset`
  - `.artifact-card`
  - `.trace-panel`
  - `.context-packet`
  - `.editorial-cover`
  - `.motion-reveal`

Acceptance:

- templates no longer define competing nav languages
- core cards share a recognizable Kyanite material system
- CSS can be audited by section without archaeology

### Phase 2 - Voronoi Material Pass

Goal: replace grid/noise/source-map styling with crystalline Voronoi material.

Tasks:

- Generate or create the three Voronoi assets:
  - field
  - slab
  - proof
- Replace decorative grid backgrounds in global, hero, band, page-hero, logo-stage, and card pseudo-elements.
- Tune opacity by context:
  - body: 0.18 to 0.35
  - hero/page hero: 0.28 to 0.55
  - cards: 0.08 to 0.18
- Add CSS variables:
  - `--texture-voronoi-field`
  - `--texture-voronoi-slab`
  - `--texture-voronoi-proof`
- Create reduced-motion fallback that freezes any ambient drift.
- Check text contrast after texture replacement.

Acceptance:

- the site no longer reads as grid/noise/HUD
- Voronoi texture is visible as material, not decoration
- project images still dominate the visual hierarchy
- no text readability regression

### Phase 3 - Motion System

Goal: add tasteful life without overwhelming the site.

Tasks:

- Create `static/js/kyanite-motion.js`.
- Move duplicated `IntersectionObserver` reveal scripts out of templates into the shared file.
- Use data attributes:
  - `data-reveal`
  - `data-reveal-group`
  - `data-motion-depth`
- Add staggered reveal for:
  - project cards
  - blog cards
  - product cards
  - implementation panels
- Add hover motion:
  - proof cards: slight translate/scale, image brighten
  - product artifacts: preview lift
  - CTAs: active press, trailing mark shift
- Add mobile menu motion:
  - hamburger morph already exists; improve menu link stagger
  - keep keyboard and Escape behavior
- Add form feedback motion:
  - sending state
  - success/error status reveal
- Add `prefers-reduced-motion` rule:
  - disable ambient movement
  - disable reveal transforms
  - preserve opacity changes or instant visible state

Acceptance:

- no `transition: all`
- no animation of layout properties
- reduced motion is respected
- motion makes page state clearer
- mobile remains calm and fast

### Phase 4 - Page-Level Visual Remediation

Goal: propagate the proof-wall quality across every page.

#### Homepage

Tasks:

- Keep large logo hero image.
- Replace grid/source-map hero texture with Voronoi slab.
- Rewrite hero line and CTAs:
  - `Turn public repos into working AI systems.`
  - `Get a Tool Working`
  - `Inspect the Public Proof`
- Make `mcp-video` the strongest flagship proof bridge.
- Replace process language in support/contact sections.
- Add subtle section-to-section motion rhythm.

Acceptance:

- first viewport immediately signals Kyanite, public proof, and paid path
- hero image/logo is visible and central to brand identity
- movement is present but quiet

#### Proof Wall

Tasks:

- Keep all generated project images.
- Add one outcome line per project:
  - what this unlocks
  - what kind of blocker it solves
- Use Voronoi proof texture as card shell, not as image overlay.
- Add hover motion only on image and material frame.

Acceptance:

- proof cards feel like the core brand object
- images are not decorative; they communicate product/project identity

#### Shop

Tasks:

- Generate product-specific artifact covers.
- Replace text-only product cards with visual artifact cards.
- Change CTA from `View details` to `See What's Inside`.
- Add preview contents:
  - file list
  - sample page
  - how to use
  - who it is for
  - not for
- Keep product copy practical, not hypey.

Acceptance:

- shop feels like Kyanite artifact commerce, not a prompt-pack shelf
- buyer can understand the object before clicking

#### Product Detail Pages

Tasks:

- Add hero/product cover art.
- Add sections:
  - What You Get
  - Who This Is For
  - Inside The Download
  - How To Use It
  - Not For
  - Buyer Questions
- Improve purchase panel hierarchy.
- Keep Ko-fi CTA clear.

Acceptance:

- product page answers what changes after purchase
- page has enough proof to justify buying

#### Implementation Page

Tasks:

- Rewrite lead around repo/blocker/setup path.
- Move PuenteWorks/legal framing lower.
- Create a visual `implementation trace` module:
  - repo/source
  - blocker
  - setup path
  - commands/config
  - handoff note
- Replace generic cards with asymmetric trace panels.
- Change CTA to `Send the Implementation Brief`.

Acceptance:

- paid help is understandable without sounding like generic consulting
- visitor knows what to bring and what they may get back

#### Intake Page

Tasks:

- Rewrite H1:
  - `Send the blocker before buying anything.`
- Rename fields:
  - repo/demo/source link
  - what are you trying to make work?
  - where does it break?
  - what would count as done?
- Add context-packet visual panel.
- Keep form calm and dense enough for serious requests.
- Improve inline status/error handling.

Acceptance:

- form feels like a diagnostic intake, not a generic contact form
- copy reduces anxiety and sets boundaries

#### Blog

Tasks:

- Generate editorial covers by blog cluster:
  - MCP implementation
  - repo intelligence
  - agent systems
  - AI discovery/GEO
  - build notes
- Make cards image-led.
- Keep `Published lab notes only.`
- Rewrite post CTA:
  - `Want this working in your environment?`

Acceptance:

- blog feels like public lab memory, not a plain article index
- every post routes to proof/help without over-selling

#### About

Tasks:

- Keep founder credibility.
- Add stronger lab/proof visual linkage.
- Keep portrait if it helps trust.
- Remove internal org-structure repetition.

Acceptance:

- about page explains why Kyanite exists and why the work is trustworthy

#### Spanish

Tasks:

- Fix `Contactoo`.
- Create bilingual glossary.
- Decide which English technical terms stay intentionally.
- Review line lengths on mobile.
- Make Spanish copy native, not mechanical.

Acceptance:

- Spanish routes look intentional and premium
- no broken replacement artifacts

### Phase 5 - Copy Remediation

Goal: sharpen public language around concrete user situations.

Use more:

- repo
- blocker
- command
- config
- install path
- first run
- example
- build note
- diagnostic report
- context packet
- handoff note
- proof role

Use less:

- implementation
- tool
- surface
- outcome
- usable
- proof
- handoff

CTA matrix:

- Homepage primary: `Get a Tool Working`
- Homepage secondary: `Inspect the Public Proof`
- Proof cards: `Open Repo`
- Blog page: `Read the Notes`
- Blog post service CTA: `Send the Implementation Brief`
- Shop card: `See What's Inside`
- Product detail: `Buy the Download on Ko-fi`
- Intake submit: `Send the Implementation Brief`
- Contact form: `Send the Context`

Acceptance:

- copy sounds like a real builder explaining real artifacts
- no public copy feels like internal process notes

### Phase 6 - SEO/GEO And AI Context Tone Pass

Goal: keep strong AI discovery without leaking internal scaffolding.

Tasks:

- Update `/llms.txt`.
- Update `/llms-full.txt`.
- Update `ai-sitemap.json` copy fields if needed.
- Remove process-leak phrases from machine-readable files.
- Keep SEO/GEO vocabulary inside the SEO/GEO article, not homepage sales copy.

Acceptance:

- AI assistants can quote Kyanite accurately
- public machine-readable files sound like polished brand copy

### Phase 7 - Verification And QA

Run after every major phase:

- `python3 -m pytest tests/test_landing_smoke.py -q`
- `git diff --check`
- rendered route scan for:
  - `Contactoo`
  - process-leak phrases
  - unrelated client/prospect routes
  - public Cerafica routes if not intended
- screenshot review:
  - desktop homepage
  - desktop proof wall
  - desktop shop
  - desktop product page
  - desktop implementation
  - desktop intake
  - desktop blog
  - desktop Spanish homepage
  - mobile homepage
  - mobile shop
  - mobile intake
- visual QA:
  - no text overlap
  - no broken image framing
  - no motion overload
  - no unreadable texture
  - no tap targets below target size
  - no layout shift from dynamic content
- accessibility QA:
  - skip link works
  - focus states visible
  - reduced motion works
  - image alt text correct
  - form labels and status regions correct

## Implementation Branch Strategy

Use small commits by remediation unit:

1. public-surface lock
2. Spanish replacement fix
3. CSS system cleanup
4. Voronoi texture assets
5. motion system
6. homepage/proof pass
7. shop/product pass
8. implementation/intake pass
9. blog/about pass
10. AI context/copy scanner
11. final QA

Do not mix Cerafica route boundary changes with visual texture work.

Do not mix copy rewrites with motion system infrastructure unless a section needs both to verify.

## Acceptance Definition For "Best Possible Design"

The site is ready when:

- The homepage, shop, implementation, intake, blog, and product pages all feel like the same Kyanite world.
- The generated project images are clearly the design canon.
- Voronoi texture has replaced decorative grid/noise language.
- Motion is visible but calm, purposeful, reduced-motion safe, and compositor-friendly.
- Product and service pages are visually proof-led, not text-card-led.
- Spanish pages no longer reveal machine replacement artifacts.
- Public route and API surfaces do not expose unrelated client/prospect work.
- Copy names concrete artifacts and visitor blockers.
- Screenshots look intentionally designed on desktop and mobile.
- The site does not resemble default AI design, SaaS card grids, glassmorphism, prompt-pack commerce, or generic consulting.

## First Sprint Recommendation

Start with a small but high-leverage sprint:

1. Fix `Contactoo`.
2. Gate/split Cerafica public namespace.
3. Add public-surface scanner tests.
4. Create first Voronoi texture set.
5. Replace global/hero grid texture with Voronoi.
6. Add shared `kyanite-motion.js`.
7. Verify homepage desktop/mobile screenshots.

Why this first:

It removes trust leaks and proves the new material/motion system before touching every page.

