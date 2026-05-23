# KyaniteLabs Site Unification Audit

Date: 2026-05-14

Scope inspected:
- Live homepage: https://kyanitelabs.tech/
- Live shop: https://kyanitelabs.tech/shop
- Live Productization Audit page: https://kyanitelabs.tech/offers/productization-audit
- Live Productization Intake page: https://kyanitelabs.tech/offers/productization-audit/intake
- Live llms.txt: https://kyanitelabs.tech/llms.txt
- Local source: `templates/landing-v2.html`, `app.py`, `KyaniteLabs/brand-identity.md`, `KyaniteLabs/brand-bio.md`

## Executive Diagnosis

Kyanite already has the right ingredients: dark technical atmosphere, public proof, agent-native tooling, a real logo system, and a strong public-build posture. The problem is that the site, shop, offer pages, and social/video language are not unified enough.

The homepage says:

> We turn weird AI workflows into usable tools.

The videos now say:

> Kyanite is a sharp, glitchy, cinematic AI lab that can explain complex agentic systems in public.

The shop says:

> Prompt packs and Claude Code downloads.

The offer pages say:

> A sober purple productization consulting offer.

These are related, but they do not yet feel like one brand system.

The unified brand should be:

> KyaniteLabs turns chaotic AI workflows into inspectable agent-native products: MCP servers, automation tools, launch surfaces, demos, and public proof.

## Recommended Brand Spine

### Core Promise

Use this everywhere:

> From weird workflow to usable AI tool.

Expanded:

> KyaniteLabs turns messy AI workflows, repos, and agent ideas into installable, explainable, public products.

### Brand Position

Kyanite is not a generic AI agency, a prompt shop, or a soft SaaS consultancy.

Kyanite is a public AI product lab:
- agent-native
- repo-backed
- cinematic and technical
- proof-first
- allergic to vague AI theater

### Emotional Register

The brand should feel like:
- a corrupted lab signal resolving into a usable tool
- sharp crystalline tech, not bubbly startup AI
- public proof, not mystery consulting
- weird enough to be memorable, disciplined enough to be trusted

## Visual System

### Current Strengths

The homepage hero is the strongest current page. It already uses:
- dark base
- Kyanite crystal imagery
- cyan/magenta/blue accents
- sharp copy
- public GitHub proof

This should become the source of truth for every other page.

### Current Drift

The shop and offer pages use a different visual dialect:
- more purple than Kyanite cyan/magenta
- no logo image system
- no crystalline/HUD texture
- generic card styling
- emoji icons that feel less premium than the homepage

The audit/intake pages feel serviceable but not branded enough.

### Unified Palette

Primary:
- Void: `#05070B`
- Midnight: `#080D14`
- Basalt: `#0B131D`
- Kyanite Cyan: `#26E6FF`
- Electric Blue: `#087DCC`
- Signal Magenta: `#FF2F6D`
- Text: `#F3F8FF`
- Muted Text: `#7F94A6`

Use sparingly:
- Amber/Gold only for human/attention moments
- Green only for status, success, or accepted proof

Avoid:
- default purple as the main CTA color
- soft glow as the main visual effect
- emoji-led product identity

### Typography

Current site uses Inter everywhere. Inter is readable, but it is too neutral to carry the whole brand.

Recommended:
- Display: Space Grotesk, Sora, or Manrope
- Body: Inter
- Technical labels/HUD: JetBrains Mono or IBM Plex Mono

Use mono for:
- section labels
- repo tags
- proof chips
- product metadata
- status language like `PUBLIC REPO`, `MCP SERVER`, `AGENT SURFACE`

### Motion And Texture

Use sharp digital artifacts, not dreamy softness:
- thin scanlines
- crystalline grid lines
- subtle chromatic edge offsets
- hard HUD dividers
- small glitch bursts on hover/focus
- no bokeh, no soft blobs, no over-glow

The video language can translate to the site as restrained interactive texture. The site should not become chaotic, but it should feel alive.

## Content System

### What Works

The homepage copy has good instincts:
- "weird AI workflows"
- "usable tools"
- "proof is public on GitHub"
- "not vague AI consulting"
- "repo truth"

The strongest content idea is public proof. Keep that.

### What Needs Tightening

The copy overuses a few phrases:
- product truth
- repo truth
- public surface
- inspectable proof

These are good phrases, but repeated too often they start to feel abstract. The site needs more concrete examples earlier.

Bring `mcp-video` forward as the flagship proof, especially after the Infinite Monkey video process. It is the clearest bridge between the social brand and the website.

### Homepage Hero Recommendation

Current H1:

> Kyanite turns weird AI workflows into usable tools.

Recommended hierarchy:

H1:

> KyaniteLabs

Hero line:

> From weird workflow to usable AI tool.

Supporting copy:

> We turn real repos, MCP ideas, media pipelines, and internal agent workflows into installable products with docs, demos, tests, launch surfaces, and public proof.

Primary CTA:

> Productize a workflow

Secondary CTA:

> See public tools

### Add A Social Proof Bridge

Add one section near the top:

Title:

> Built in public. Shipped as tools.

Content:
- Infinite Monkey video system: generated visuals, MCP video effects, voice pipeline, social distribution
- mcp-video: agent-facing video editing stack
- Epoch: estimation and planning tool
- DialectOS: localization QA

This helps a TikTok/Shorts viewer land on the site and immediately recognize the same brand universe.

## Information Architecture

### Current Nav

Approach, Proof, Offers, Shop, Projects, Contact, Product Intake

### Recommended Nav

Tools, Proof, Offers, Lab Notes, Shop, Contact, Product Intake

Rationale:
- "Approach" is less interesting than the actual tools.
- "Proof" and "Projects" currently overlap.
- "Lab Notes" creates a home for videos, essays, build logs, and public experiments.
- "Shop" should be reframed as operator assets, not a disconnected prompt-pack shelf.

## Page-Specific Findings

### Homepage

Keep:
- dark hero
- crystal visual
- public repo proof
- anti-generic-consulting stance
- productization audit as first offer

Change:
- reduce vertical dead air between sections
- make `mcp-video` more prominent above the fold or directly below hero
- use mono/technical typography for labels and proof chips
- add a video/social bridge section
- make fade-up content visible by default for no-JS and static captures

Technical note:

The `.fade-up` cards are `opacity: 0` until IntersectionObserver marks them visible. Full-page screenshots and no-JS contexts can show large empty sections. Safer pattern:

```css
.fade-up { opacity: 1; transform: none; }
.js .fade-up { opacity: 0; transform: translateY(24px); }
.js .fade-up.visible { opacity: 1; transform: none; }
```

Then add `document.documentElement.classList.add('js')` before observing.

### Shop

Current issue:

The shop feels like a separate purple Claude Code mini-site. It uses emoji icons and a different CTA language.

Fix:
- use the same nav/logo/hero treatment as homepage
- replace emoji icons with crystalline monogram tiles or mono product codes
- rename "Digital Products" to "Operator Assets"
- connect products to the bigger Kyanite promise

Suggested copy:

> Operator Assets
> Downloadable systems for people building with AI agents: prompts, repo structures, Claude Code workflows, and productization templates.

### Productization Audit

Current issue:

The offer is clear, but visually calmer and more generic than the homepage.

Fix:
- inherit homepage tokens and nav
- use a sharper title treatment
- show a sample deliverable outline
- add "based on public Kyanite tools" proof cards
- use cyan/magenta CTA instead of purple

### Intake

Current issue:

The intake page is functional but visually plain.

Fix:
- same nav and footer as the rest of the site
- add a small "What happens next" panel
- add "this is not a sales trap" style reassurance in Kyanite's direct voice
- use shorter field help text with mono labels

## Priority Implementation Plan

1. Extract shared design tokens and nav/footer partials so homepage, shop, audit, and intake cannot drift.
2. Replace purple shop/audit styling with the homepage cyan/blue/magenta system.
3. Add a `Lab Notes` or `Built in Public` section that bridges social videos to product proof.
4. Promote `mcp-video` as flagship public proof.
5. Update typography: display font plus mono technical labels.
6. Fix fade-up no-JS/static-capture behavior.
7. Rewrite repeated abstract copy into concrete examples.
8. Rename or reposition the shop as operator assets.
9. Create a style guide page or markdown file for future agents.

## Bottom Line

The site is not bad. It is actually close. The homepage has the right bones.

The problem is brand fragmentation:
- homepage: Kyanite product lab
- videos: cinematic glitch AI lab
- shop: Claude Code prompt shop
- audit pages: subdued consulting offer

Unify around one idea:

> KyaniteLabs makes weird AI workflows real enough to inspect, install, ship, and buy.

