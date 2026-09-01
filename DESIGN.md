---
name: Bitcoin Analysis
description: A sovereign Bitcoin analysis and position-reconciliation workspace.
colors:
  bitcoin-signal: "#F7931A"
  bitcoin-hover: "#FFA42D"
  bitcoin-soft: "#FFB45A"
  ledger-black: "#07090A"
  panel-black: "#0B0D0F"
  track-charcoal: "#1B1E20"
  text-primary: "#FFFFFF"
  text-secondary: "#FFFFFFB8"
  text-muted: "#FFFFFF73"
  divider: "#FFFFFF12"
  gain: "#34D399"
  loss: "#F87171"
typography:
  display:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "24px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "20px"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: "normal"
  body:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 500
    lineHeight: 1.35
    letterSpacing: "normal"
  numeric:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: "normal"
    fontFeature: "tnum"
rounded:
  sm: "8px"
  control: "10px"
  card: "12px"
  panel: "14px"
  pill: "9999px"
spacing:
  xxs: "4px"
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "20px"
  xl: "24px"
  xxl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.bitcoin-signal}"
    textColor: "{colors.ledger-black}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
    height: "32px"
  button-primary-hover:
    backgroundColor: "{colors.bitcoin-hover}"
    textColor: "{colors.ledger-black}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
    height: "32px"
  button-ghost:
    backgroundColor: "#00000000"
    textColor: "{colors.text-secondary}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
    height: "32px"
  chip-active:
    backgroundColor: "#F7931A1F"
    textColor: "{colors.bitcoin-soft}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "6px 8px"
  panel:
    backgroundColor: "{colors.panel-black}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.panel}"
    padding: "16px"
  input-search:
    backgroundColor: "{colors.ledger-black}"
    textColor: "{colors.text-primary}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0 12px"
    height: "36px"
  navigation-active:
    backgroundColor: "#F7931A1F"
    textColor: "{colors.text-primary}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
---

# Design System: Bitcoin Analysis

## Overview

**Creative North Star: "The Orange Ledger"**

The interface is a precise Bitcoin ledger viewed through a modern analytical command center. A focused investor uses it in low ambient light, on a wide desktop, to compare market evidence with personal purchases and open positions before making a decision. Dark surfaces are therefore structural, not atmospheric decoration.

Prototype A defines the reading order: market evidence, personal ledger, exposure, risk, and source status. Prototype C supplies the interaction grammar: analytical layers can be switched on the same timeline, and personal events appear as synchronized waypoints. Prototype D defines the visual finish: compact navigation, restrained orange signals, tonal depth, and dense panels with an immediate hierarchy.

The system rejects exchange urgency, generic crypto noise, neon terminal cosplay, and interchangeable SaaS cards. Desktop favors deliberate density. Mobile collapses navigation and stacks the same tasks without changing labels, order, or meaning. State transitions last 150 to 200 ms and communicate selection, disclosure, or feedback only.

**Key Characteristics:**

- Bitcoin-only and evidence-led
- Dense, calm, and immediately scannable
- One continuous timeline across market and personal data
- Tonal depth instead of decorative glass or wide shadows
- Orange reserved for Bitcoin, active state, and primary action

## Colors

The palette is a restrained black field with one unmistakable Bitcoin signal and separate semantic colors for outcomes.

### Primary

- **Bitcoin Signal** (`#F7931A`): Bitcoin marks, the primary action, active navigation, selected analytical layers, progress, and the principal chart trace.
- **Bitcoin Hover** (`#FFA42D`): hover and pressed feedback for primary actions. It never becomes a second accent family.
- **Bitcoin Soft** (`#FFB45A`): readable orange text on dark surfaces for active labels, dates, and compact badges.

### Neutral

- **Ledger Black** (`#07090A`): page canvas, sidebar, inset controls, and the deepest chart field.
- **Panel Black** (`#0B0D0F`): primary panels, utility header, risk modules, and portfolio containers.
- **Track Charcoal** (`#1B1E20`): progress tracks, radial-meter remainder, and rare raised neutral states.
- **Primary Text** (`#FFFFFF`): headings, essential values, and selected navigation.
- **Secondary Text** (`#FFFFFFB8`): supporting values and readable body copy.
- **Muted Text** (`#FFFFFF73`): metadata, descriptions, and inactive labels. Never use a lower opacity for essential information.
- **Divider** (`#FFFFFF12`): structural separators, quiet borders, and table rules.

### Tertiary

- **Gain** (`#34D399`): positive return, healthy state, and confirmed live status.
- **Loss** (`#F87171`): negative return, destructive state, and material risk breach.

### Named Rules

**The Ten Percent Orange Rule.** Bitcoin Signal occupies no more than roughly ten percent of a screen. Its rarity creates hierarchy.

**The Semantic Override Rule.** Gains stay green and losses stay red. Brand orange never replaces financial meaning.

**The No Glass Rule.** Panels use opaque tonal surfaces. Decorative blur, transparent glass cards, gradient text, and wide orange glow are prohibited.

## Typography

**Display Font:** Inter with `ui-sans-serif` and `system-ui` fallbacks  
**Body Font:** Inter with `ui-sans-serif` and `system-ui` fallbacks  
**Numeric Font:** Inter with tabular figures

**Character:** One disciplined sans family keeps the application familiar and operational. Weight, opacity, and tabular alignment create hierarchy without introducing a display face or terminal aesthetic.

### Hierarchy

- **Display** (600, `24px`, 1.2): page titles and the primary dashboard heading only.
- **Headline** (600, `20px`, 1.25): major values, position totals, and panel-level emphasis.
- **Title** (600, `14px`, 1.35): panel headings, selected items, and action names.
- **Body** (400, `13px`, 1.5): explanations and decision notes, capped at 70 characters per line when prose is present.
- **Label** (500, `11px`, 1.35): navigation, controls, status labels, and table headers.
- **Numeric** (600, `14px`, 1.35, tabular figures): prices, percentages, quantities, timestamps, and risk values.

### Named Rules

**The Stable Number Rule.** Every changing financial value uses tabular figures so updates never shift adjacent content.

**The Quiet Label Rule.** Labels use sentence case. Uppercase is limited to tickers, time ranges, and short scale markers.

**The No Terminal Costume Rule.** Monospace may identify source IDs or raw timestamps, but never becomes the default interface face.

## Elevation

The system is flat by default and creates depth with neighboring dark tones, fine dividers, and local contrast. Cards do not float above the canvas. A panel may use a restrained orange radial wash near a Bitcoin chart, capped at low opacity, but not a decorative glow. Shadows are reserved for content that genuinely overlays the workspace.

### Shadow Vocabulary

- **Overlay** (`0 8px 24px rgba(0, 0, 0, 0.28)`): popovers, command results, and menus that sit above the application shell.
- **Focus Halo** (`0 0 0 3px rgba(247, 147, 26, 0.18)`): keyboard focus on the active control, paired with a solid outline.

### Named Rules

**The Tonal First Rule.** Use Ledger Black beside Panel Black before adding any shadow.

**The Earned Shadow Rule.** Static cards never cast shadows. Only overlays and keyboard focus may leave the surface plane.

## Components

Components are compact, familiar, and state-complete. Every interactive element defines default, hover, focus-visible, active, disabled, loading, and error behavior where relevant.

### Buttons

- **Shape:** compact rounded rectangle (`10px`) with a standard height of `32px`; icon-only controls may be `36px` square.
- **Primary:** Bitcoin Signal background, Ledger Black text, `8px 12px` padding, and one clear verb plus object.
- **Hover / Focus:** Bitcoin Hover on pointer hover; Focus Halo plus a solid Bitcoin Signal outline on keyboard focus; pressed state moves by no more than `1px`.
- **Secondary / Ghost:** transparent or Ledger Black background with Secondary Text. Hover uses a four-percent white tonal fill, never orange fill.
- **Disabled / Loading:** preserve the control width, reduce contrast, block interaction, and replace the leading icon with a compact progress indicator when loading.

### Chips

- **Style:** analytical layers and time ranges use an `8px` radius, `6px 8px` padding, and Label typography.
- **State:** selected chips use a twelve-percent Bitcoin Signal tint with Bitcoin Soft text. Unselected chips remain neutral and retain a visible hover state.
- **Behavior:** layer chips are toggle buttons with `aria-pressed`. Desktop places them beside or above the chart; mobile uses a horizontally scrollable row.

### Cards / Containers

- **Corner Style:** KPI cards use `12px`; dominant chart, risk, and ledger panels use `14px`.
- **Background:** Panel Black on Ledger Black. Nested cards are prohibited; internal groups use spacing and Divider rules.
- **Shadow Strategy:** flat at rest, following the Tonal First Rule.
- **Border:** use Divider only when it clarifies grouping. Do not add a border and a wide shadow to the same surface.
- **Internal Padding:** `16px` on compact cards and mobile; `20px` on desktop analytical panels.

### Inputs / Fields

- **Style:** Ledger Black field inside Panel Black, `10px` radius, `36px` height, Secondary Text, and a visible label or accessible name.
- **Focus:** Bitcoin Signal outline plus Focus Halo. Placeholder contrast must remain readable and never stand in for a label.
- **Error / Disabled:** Loss identifies errors alongside text; disabled fields remain legible and cannot be mistaken for missing data.

### Navigation

- **Desktop:** a `208px` sidebar with icon and label pairs. Active navigation uses a twelve-percent Bitcoin Signal tint, white text, orange icon, and a small orange state dot.
- **Mobile:** a compact top identity bar followed by the four highest-priority destinations. Secondary destinations move into an explicit menu, not an unlabeled icon.
- **States:** inactive items use Muted Text; hover adds a four-percent white tonal fill; focus remains fully visible.

### Chart and Analytical Layers

- The chart is the dominant evidence surface and shares one time axis with purchases, positions, on-chain signals, derivatives, macro context, and decision waypoints.
- Layer toggles never reload or replace the timeline. They update overlays in place and expose an active-layer count.
- Hovering or focusing a waypoint highlights the matching ledger row. Selecting a ledger row moves the chart cursor to the same timestamp.
- Essential chart values remain available in an accessible table or summary outside the canvas.

### Ledger, Risk, and Provenance

- Desktop uses a compact table for date, event, amount, execution, status, and return. Mobile converts each record into a two-line disclosure row without dropping essential fields.
- Risk values, leverage, liquidation context, source freshness, and completeness stay visible near the relevant position.
- Demo, delayed, estimated, incomplete, and read-only states use explicit badges and supporting text. Color is never the only state indicator.

## Do's and Don'ts

### Do:

- **Do** use prototype A's reading order: market evidence, personal ledger, exposure, risk, and provenance.
- **Do** keep prototype C's layer toggles and waypoints synchronized to one continuous timeline.
- **Do** use the restrained black and Bitcoin Signal system from prototype D, with orange limited to Bitcoin, selection, and primary action.
- **Do** keep desktop dense and mobile sequential while preserving labels, task order, and essential risk information.
- **Do** label demo, delayed, estimated, incomplete, and read-only data at the point where it appears.
- **Do** use familiar financial controls, visible keyboard focus, readable contrast, and tabular figures.

### Don't:

- **Don't** build generic multi-asset crypto dashboards where Bitcoin competes with token rankings, promotions, or market noise.
- **Don't** copy exchange interfaces that prioritize order placement, leverage promotion, or urgency over analysis and risk context.
- **Don't** use neon trading-terminal cosplay, decorative glass panels, excessive glow, or motion without a state change.
- **Don't** use gamified profit language, confetti, streaks, fear-of-missing-out prompts, or implied financial certainty.
- **Don't** create dense screens with no clear reading order, unexplained indicators, or metrics detached from source and time.
- **Don't** use generic AI or SaaS dashboard patterns built around oversized hero metrics and interchangeable cards.
- **Don't** use gradient text, colored side stripes, custom scrollbars, nested cards, or card radii above `16px`.
- **Don't** use orange for gain or loss, or rely on color alone to communicate financial state.
