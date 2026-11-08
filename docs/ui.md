# Remi UI aesthetics

This document records the current visual direction for the Remi desktop MVP. Keep new screens consistent with these choices and update this page when the design system changes.

## Product feel

- Warm, calm, and operational: Remi should feel like a practical restaurant work tool, not a guest review or analytics dashboard.
- Use a light, paper-like canvas with warm neutral surfaces and restrained terracotta accents.
- Prefer clear hierarchy, readable text, and compact panels over oversized whitespace or decorative effects.
- Keep staff-to-Remi task conversations distinct from the separate server-to-guest workflow.

## Typography

- Use Verdana throughout the desktop app, including controls and form fields.
- Keep text comfortably readable at the default UI scale. Supporting labels should remain legible and should not be reduced to tiny captions.
- Use medium-to-bold weights for headings and important labels; use regular weights for explanatory copy.

## Color and surfaces

- Primary accent: warm terracotta, currently centered around `#b85c42`.
- Main canvas: warm off-white (`#f8f4ef`) with white or cream panels (`#fffdfa`).
- Text: dark warm brown (`#342923`) for primary content and softer brown-gray tones for secondary content.
- Borders: subtle warm beige (`#eadfd5` / `#e9ded4`).
- Use sage green for healthy/approved states and muted gold for configured or pending states. Reserve red for errors and unavailable services.
- The Remi chef mark sits on a light neutral field so it remains distinct from its warm artwork.

## Icons and controls

- Use simple Heroicons-inspired outline SVGs with rounded joins and consistent stroke weight.
- Use rounded corners sparingly and consistently across buttons, chips, fields, panels, and avatars.
- Primary actions use filled terracotta buttons; secondary actions use light surfaces with warm borders.
- The frameless Electron window uses a custom title bar with Remi identity, zoom controls, and window controls. Zoom is available with the title-bar controls, Display settings, and Ctrl/Cmd `+`, `-`, and `0`.

## Layout and interaction

- Keep the sidebar fixed and fitted within the window. Let the main content area scroll when a page needs more room.
- Use denser spacing where it improves scanability, while preserving clear grouping and readable line height.
- Keep agent transcript and context visible together on the Staff assistant page.
- Settings use a modal with sections for Display, Connections, Voice agent, Daytona, personal Agent instructions, and shared Workplace instructions.
- Show service state with a concise status plus explanatory detail. Distinguish live status from demo-only controls.
- Preserve visible confirmation and review steps before operational changes; schedules require manager approval in the MVP.

## Existing visual references

- Desktop implementation: [apps/desktop](../apps/desktop/README.md)
- Shared Remi and menu artwork: [public](../public/)
- The desktop app currently applies these styles in `apps/desktop/src/style.css` and renders shared interface components in `apps/desktop/src/main.jsx`.
