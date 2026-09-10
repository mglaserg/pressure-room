# Pressure Room — Design System

## North star

Pressure Room should feel like a **premium creative workspace**, not a developer dashboard.

The interface should help a writer stay with the story longer. Calmness, hierarchy, spacing, and typography are therefore functional requirements.

## Visual character

- **Cinematic, restrained, editorial**
- warm graphite rather than pure black
- warm paper for the screenplay surface
- brass used sparingly for interaction, selection, and causality
- muted brick red for BUT / danger / escalating cost
- low-contrast borders; whitespace does most of the grouping
- no neon gradients, glowing SaaS cards, or dense metric-dashboard styling

## Typography

Typography is deterministic across platforms and has no runtime font-CDN dependency. Next.js `next/font` downloads the files during the build and serves them with the application.

- UI: **Inter**
- Story hierarchy: **Newsreader**
- Screenplay: **Courier Prime**
- UI sizing uses the seven-step token scale; meaningful interface text does not drop below `--type-xs` (`0.75rem`).
- Font weights use real 400 / 500 / 600 / 700 / 800 steps instead of synthetic in-between values.

## Token discipline

Components consume semantic surface, text, status, radius, and type tokens. New one-off hex colors, font sizes, and radii should be treated as design-system exceptions that need an explicit reason.

The screenplay is the intentional exception: Page mode follows screenplay conventions rather than the general UI type scale.

## Interaction hierarchy

Every screen should answer one obvious question:

- **Write:** What is the scene?
- **Story:** What is this story really about?
- **Characters:** Who is under pressure?
- **Causality:** Why does the next scene have to happen?
- **Bills:** What does the choice cost?
- **Diagnose:** Where is the pressure actually moving?

Advanced controls are progressively disclosed.

## Mobile

Mobile is a writing companion, not a squeezed desktop application.

- bottom primary navigation
- swipeable scene strip
- large touch targets
- single-column structural forms
- causality reflows vertically
- screenplay remains the dominant surface
- modals become bottom sheets

## Product rule

**Power underneath. Calm on the surface.**
