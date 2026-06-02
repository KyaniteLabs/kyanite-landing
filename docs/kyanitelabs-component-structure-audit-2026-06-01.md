# KyaniteLabs Component And Structure Audit

Date: 2026-06-01

Scope: public frontend structure, visual hierarchy, component intent, image treatment, copy surface, and page-to-page flow. Backend behavior is out of scope except where it leaks into public UX.

## BLUF

The site now has stronger raw ingredients than its structure can support: the uploaded hero artwork, project image gallery, and Voronoi material direction are good. The problem is composition. The homepage still reads like a stack of separately-designed blocks: hero image, isolated MCP feature, full project gallery, blog preview, abstract process grid, offer menu, contact form. Each block is individually plausible, but together they do not create a disciplined narrative.

The next design pass should be structural, not decorative.

Recommended homepage story:

1. Brand artifact: show the generated KyaniteLabs hero image cleanly.
2. What this is: one short value statement and two CTAs.
3. Proof wall: the public project gallery is the main content.
4. How to use the proof: route visitors into implementation help, shop assets, or lab notes.
5. Contact/intake: one decisive conversion path.

Everything else should either support that story or be removed.

## Highest Priority Findings

### 1. Hero Image Is Good, But Its Placement Still Feels Too Huge

Current state:

- The uploaded hero image is now used directly as the first visual.
- The image is visually strong, but it dominates the first viewport.
- The image has its own rectangular dark-gray panel edge inside the artwork. Against the site background, those outer image edges are visible past the colored outline, making it feel pasted in.

Why it feels wrong:

- The hero artwork is a complete poster. The page treats it as a massive block instead of integrating it as the top surface of the site.
- The surrounding page background is not close enough to the artwork's border texture, so the image rectangle is legible.
- The text beneath the image now feels like an afterthought rather than part of the same composition.

Recommendation:

- Keep the exact uploaded image.
- Reduce max visual width from the current very large treatment to roughly 1120-1200px on desktop.
- Blend only the outer image edge into the page background using a very subtle edge feather or matching material field behind it. Do not place overlays across the logo or center of the artwork.
- Put the hero text in a compact band immediately below the image, with enough spacing that the artwork remains primary but does not consume the whole first experience.
- Do not add frames, backplates, cut corners, or pseudo-elements over the image.

Pass criteria:

- The image feels like it belongs to the page, not like a screenshot placed on top of the page.
- The colored outline remains visible.
- The logo remains untouched.
- The first viewport hints at the next section on desktop and mobile.

### 2. The MCP Video Feature Section Is Structurally Wrong

Current state:

- Immediately after the hero, the site shows a giant `Flagship Proof // mcp-video` card plus a signal board.
- The full public project gallery appears directly after it.

Why it feels wrong:

- It creates a false hierarchy: mcp-video looks like the one primary product, but the brand is now positioned around the full Kyanite project ecosystem.
- The section duplicates the proof gallery instead of preparing the visitor for it.
- The signal board is abstract and does not add enough information to justify its footprint.
- It makes the page feel like it has an abandoned feature module from an older strategy.

Recommendation:

- Remove the giant MCP-only section entirely, or replace it with a compact "What Kyanite builds" orientation strip.
- If mcp-video remains highlighted, make it one of three flagship examples, not the only giant one.
- Better replacement:
  - "The Kyanite pattern"
  - 3 small lanes: Tool, Proof, Handoff
  - each lane references multiple projects, not one.

Pass criteria:

- The project gallery becomes the first major proof section after the hero.
- No visitor asks, "why is this one repo getting a huge empty section?"

### 3. Homepage Structure Is Too Generic Because It Has Too Many Abstract Sections

Current sequence:

1. Hero
2. Tools / MCP feature
3. Public Proof gallery
4. Blog preview
5. Outcome Model
6. Products + Support
7. Contact

Structural issue:

- The sections do not build on each other tightly enough.
- "Outcome Model" is conceptually true but generic.
- "Products + Support" is useful but too broad and card-heavy.
- The blog preview interrupts the conversion path before the page has finished explaining how to use the proof.

Recommended sequence:

1. Hero artwork and short value statement.
2. Public Proof gallery.
3. "How to use this proof" conversion router:
   - Install/adapt a Kyanite tool.
   - Browse operator assets.
   - Read lab notes.
4. Selected lab notes, only after the proof has context.
5. Contact/intake.

Pass criteria:

- Every section answers the question created by the section before it.
- No section exists because "a landing page usually has this."

### 4. The CSS Cascade Carries Too Many Old Design Decisions

Current state:

- The CSS contains multiple generations of hero, grid, card, texture, and image treatment rules.
- Later overrides are masking older rules instead of replacing them.
- This caused the exact failure the user called out: good assets were damaged by inherited presentation layers.

Why it matters:

- The design will keep regressing because old rules still exist.
- Visual QA becomes harder because the source of truth is not obvious.
- Future agents will accidentally fight the cascade instead of designing the page.

Recommendation:

- Create a clean "homepage v3" CSS section or extract homepage-specific rules into a scoped layer.
- Delete obsolete hero image plate rules, old source-map texture rules, and old generated matte pass rules once the new direction is accepted.
- Keep a short comment explaining the invariant: "Do not frame or overlay the generated hero artwork."

Pass criteria:

- One place defines the hero layout.
- One place defines material textures.
- One place defines project cards.

## Component Audit

### Top Navigation

What works:

- Brand mark is visible.
- Navigation has clear destinations.
- Implementation Help CTA is directionally correct.

Problems:

- The nav still feels like a standard SaaS nav.
- "Tools," "Proof," "Support," and "Shop" overlap semantically.
- The new icon is good, but the nav does not yet feel integrated with the hero artwork's material system.

Recommendation:

- Keep the nav compact.
- Consider renaming:
  - Tools -> Projects
  - Proof -> Proof Wall
  - Support -> Get Help
- Keep only one primary CTA.

### Hero Artwork

What works:

- The uploaded image is the right brand direction.
- The logo is unmistakable.
- The Voronoi/material concept is present in the image itself.

Problems:

- Too large in the current layout.
- The image rectangle edge is visible.
- The text below it is detached.

Recommendation:

- Show the image at a more deliberate max width.
- Use a matching material background behind it.
- Use only edge blending if needed.
- No frame, no extra overlay, no crop, no pseudo-element treatment over the image.

### Hero Text And CTAs

What works:

- "Turn public repos into working AI systems" is clear enough.
- Primary CTA "Get a tool working" is good.

Problems:

- The hidden visual H1 means the actual visible brand is only inside the image. That is okay visually, but the text system below must be more intentional.
- The proof chips feel like a generic landing-page pattern.

Recommendation:

- Keep one short value statement under the hero image.
- Keep two CTAs maximum.
- Replace proof chips with one compact sentence or remove them.

### MCP Feature / Signal Board

Verdict: remove or radically compress.

Why:

- It competes with the gallery.
- It creates a product hierarchy the rest of the site does not honor.
- The signal board is abstract and not worth the space.

Replacement:

- A narrow orientation strip:
  - "Kyanite turns public repos into usable tools."
  - "Inspect the build."
  - "Install or adapt it."
  - "Leave with a handoff."

### Public Project Gallery

What works:

- This is the best section.
- The project images are the desired visual direction.
- The gallery proves range and specificity.

Problems:

- Every card has similar weight.
- 15 project cards can become a wall rather than a guided proof system.
- The section could benefit from categories or a clearer first row.

Recommendation:

- Keep the gallery.
- Add light grouping or sorting:
  - Agent tools
  - Domain tools
  - Learning/diagnostic systems
  - Media/localization
- Consider making the first row a curated "flagship row" inside the gallery, not a separate giant section.

### Proof Strip

Verdict: probably remove.

Why:

- It reads like metadata.
- It says what the gallery already demonstrates visually.

Replacement:

- If kept, turn it into filter/category navigation.

### Blog Preview

What works:

- Lab notes are important for trust.
- The content supports the build-first identity.

Problems:

- It appears before the conversion router.
- The cards are generic compared with the project images.
- It feels less visually resolved than the proof wall.

Recommendation:

- Move after the conversion router.
- Rename to "Field notes from the builds."
- Show fewer notes or connect each note to a project/category.

### Outcome Model

Verdict: currently generic.

Why:

- "Start from a real blocker / make inspectable / help people reach outcome" is true but expected.
- It does not feel specific to Kyanite's projects.

Recommendation:

- Either remove it or convert it into a more specific "Kyanite handoff model":
  - Repo
  - Working command
  - Example output
  - Docs/tests
  - Implementation path

### Products + Support

What works:

- The offer categories are useful.
- The page needs a paid path.

Problems:

- Six offer cards create menu fatigue.
- Some offers overlap with projects in the gallery.
- Pricing/scoping signals are inconsistent.

Recommendation:

- Replace with a 3-path router:
  - Get a public tool working
  - Buy an operator asset
  - Request a diagnostic/media/localization implementation
- Move detailed offer cards to `/implementation` or `/shop`.

### Contact Section

What works:

- "Bring the blocker" is the right voice.
- The form asks for context rather than generic lead capture.

Problems:

- It duplicates the implementation intake path.
- It is visually similar to other card/form patterns.

Recommendation:

- Make one primary conversion path:
  - homepage CTA -> `/implementation/intake`
  - footer email for secondary contact
- If keeping the homepage form, make it visibly lighter and shorter.

### Footer

What works:

- Basic navigation is fine.
- Brand operation line is clean.

Problems:

- It repeats links already available in nav.
- It does not yet reinforce the new visual system strongly.

Recommendation:

- Keep simple.
- Add no extra decoration.
- Make it feel like the end of the proof system, not a generic footer.

## Supporting Page Audit

### About Page

What works:

- Stronger than most supporting pages.
- Human founder context helps.
- The portrait gives the page a different register from the homepage.

Problems:

- Still card-heavy.
- The signal board repeats homepage visual language.
- The page could state Kyanite's taste and operating philosophy more directly.

Recommendation:

- Keep the portrait/story.
- Reduce repeated cards.
- Make the principles feel more editorial and less dashboard-like.

### Implementation Page

What works:

- The structure is clearer than the homepage.
- "What you bring / what Kyanite returns" is useful.

Problems:

- It lacks a visual anchor.
- Some cards still feel like generic service-page cards.
- The page should connect directly to public projects.

Recommendation:

- Add a compact project-proof strip.
- Tie implementation examples to actual repos.
- Reduce abstract explanation.

### Implementation Intake

What works:

- Form intent is clear.
- "Send the blocker before buying anything" is good.

Problems:

- Visual treatment is plain.
- The aside is useful but could be shorter.

Recommendation:

- Keep the form.
- Add a short reassurance line.
- Do not over-design this page.

### Blog Index

What works:

- The lab notes concept is appropriate.

Problems:

- It repeats the full project gallery, which makes the blog page feel like homepage v2.
- Blog cards are visually underpowered relative to project cards.

Recommendation:

- Remove the full gallery from blog index or replace it with a small "related proof" strip.
- Make blog cards more editorial.

### Shop

What works:

- Small catalog is appropriate.
- Artifact covers help.

Problems:

- Sparse page.
- Product cards do not yet show enough tangible artifact preview.

Recommendation:

- Keep simple.
- Add one preview image or sample list per product.
- Avoid making the shop feel like a generic marketplace.

## Design System Audit

### What Is Working

- Dark matte mineral direction fits Kyanite.
- Project images are the strongest visual identity.
- Voronoi material direction is now conceptually right.
- No-pill button rule is mostly respected.
- The generated hero image is the correct brand signal.

### What Is Not Working

- Too many card variants.
- Too many repeated backgrounds.
- Too many old CSS layers.
- Too many generic landing-page section types.
- Texture system can still become decoration unless it is used as material, not wallpaper.

### Missing Design Rules

Add explicit rules to the design system:

- The generated hero artwork must be shown raw. No overlays, frames, crops, filters, or pseudo-elements over it.
- Voronoi is a material effect: it changes texture, relief, and shading. It is not merely line art.
- Project images are the main proof language.
- Cards must exist only when they hold discrete objects: projects, products, posts, forms. Do not use card grids for abstract ideas unless the content is genuinely scannable.
- No isolated flagship section unless the page has a real editorial reason for the feature.

## Recommended Next Implementation Plan

### Phase 1: Homepage Structure

1. Reduce hero image max width and blend only the outer image edge.
2. Remove the giant MCP-only feature section.
3. Move proof gallery directly after hero.
4. Replace Outcome Model and Products + Support with one conversion router.
5. Keep contact/intake as the final action.

### Phase 2: Component Cleanup

1. Consolidate hero CSS into one final source of truth.
2. Delete obsolete hero plate/stage rules.
3. Consolidate card variants.
4. Make gallery/card spacing consistent.
5. Ensure mobile first viewport shows hero plus a hint of next content.

### Phase 3: Supporting Pages

1. Remove repeated full project gallery from blog index.
2. Add project-linked examples to implementation page.
3. Add tangible product previews to shop.
4. Tighten about page card usage.

## Final Verdict

The site is no longer suffering from weak assets. It is suffering from weak orchestration.

The next pass should not add more visuals. It should remove generic sections, clarify the proof-to-action path, and let the hero image plus project gallery carry the identity.

