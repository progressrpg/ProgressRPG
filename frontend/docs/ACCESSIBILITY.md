# Accessibility Guidelines

## Overview
This project follows WCAG 2.1 AA standards for accessibility.

## Testing
Run accessibility tests with:
```bash
npm run test:a11y
```

View test results in the UI:
```bash
npm run test:a11y:ui
```

View the test report:
```bash
npm run test:a11y:report
```

## Component Guidelines

### Buttons
- Always provide meaningful labels
- Use `ariaLabel` for icon-only buttons
- Ensure disabled state is communicated
- Support keyboard interaction (Enter and Space keys)

**Example:**
```jsx
<Button ariaLabel="Close modal" onClick={handleClose}>
  &times;
</Button>
```

### Forms
- All inputs must have associated labels
- Error messages must use `role="alert"`
- Use `aria-describedby` for help text
- Form fields should be grouped with `role="group"`
- Pass `disabled` state to inputs when form is submitting

**Example:**
```jsx
<Input
  id="email"
  label="Email"
  type="email"
  value={email}
  onChange={setEmail}
  error={errors.email}
  helpText="We'll never share your email"
  required
/>
```

### Modals
- Trap focus within modal
- Return focus when closed
- Support Escape key
- Use proper ARIA attributes (`role="dialog"`, `aria-modal="true"`, `aria-labelledby`)

**Example:**
```jsx
<Modal title="Confirm Action" onClose={handleClose} id="confirm-modal">
  <p>Are you sure?</p>
  <Button onClick={handleConfirm}>Yes</Button>
</Modal>
```

### Navigation
- Use semantic HTML (`nav`, `header`, `main`)
- Provide `aria-label` for navigation sections
- Ensure keyboard navigation works
- Use proper link labels with context

### Lists
- Use proper list semantics with `role="list"` or `role="listbox"` for selectable lists
- Add `aria-selected` for selectable items
- Support keyboard navigation with Tab and Enter/Space keys
- Provide meaningful `aria-label` for the list

## CSS Utilities

### Screen Reader Only Content
Use the `.sr-only` class to hide content visually while keeping it accessible to screen readers:
```jsx
<span className="sr-only">Loading...</span>
```

### Focus Indicators
All interactive elements have visible focus indicators for keyboard navigation:
- 2px solid outline
- 2px offset from element

### Reduced Motion
The application respects user motion preferences:
- Animations are reduced or disabled when `prefers-reduced-motion: reduce` is set

### High Contrast
The application supports high contrast mode for better visibility.

## Best Practices

### Loading States
Always use proper live regions for loading states:
```jsx
<div role="status" aria-live="polite" aria-busy="true">
  <span className="sr-only">Loading...</span>
</div>
```

### Error Messages
Use `role="alert"` for error messages so they're announced immediately:
```jsx
{error && <p role="alert">{error}</p>}
```

### Interactive Elements
Ensure all interactive elements:
- Can be reached with keyboard (Tab key)
- Can be activated with keyboard (Enter or Space)
- Have clear focus indicators
- Have descriptive labels or aria-labels

### Images and Icons
Always provide alternative text:
- Use `alt` attribute for images
- Use `aria-label` or `aria-labelledby` for icon buttons
- Use `aria-hidden="true"` for purely decorative icons

## Testing Checklist

Before submitting code, verify:
- [ ] All interactive elements are keyboard accessible
- [ ] All form inputs have labels
- [ ] Error messages use `role="alert"`
- [ ] Loading states use proper live regions
- [ ] Focus management works correctly (especially in modals)
- [ ] Color contrast meets WCAG AA standards
- [ ] Automated a11y tests pass (`npm run test:a11y`)

## Manual Testing

### Keyboard Navigation
1. Use Tab to navigate through interactive elements
2. Use Shift+Tab to navigate backwards
3. Use Enter or Space to activate buttons/links
4. Use Escape to close modals/drawers

### Screen Reader Testing
- **Windows:** NVDA (free) or JAWS
- **macOS:** VoiceOver (built-in, Cmd+F5)
- **Linux:** Orca

### Browser DevTools
Most browsers have accessibility inspectors:
- Chrome/Edge: DevTools > Accessibility panel
- Firefox: DevTools > Accessibility panel

## Resources

- [WCAG 2.1 AA Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/)
- [WebAIM Resources](https://webaim.org/)
- [React Accessibility Docs](https://react.dev/learn/accessibility)
- [axe-core Accessibility Engine](https://github.com/dequelabs/axe-core)
- [Playwright Accessibility Testing](https://playwright.dev/docs/accessibility-testing)

## Common Issues and Solutions

### Issue: Form submission not accessible
**Solution:** Ensure form has `noValidate` attribute and we handle validation ourselves with proper error messages using `role="alert"`.

### Issue: Modal traps focus incorrectly
**Solution:** Use the Modal component which handles focus trapping automatically.

### Issue: Loading states not announced
**Solution:** Use `role="status"` with `aria-live="polite"` and `aria-busy="true"`.

### Issue: Icon-only buttons have no label
**Solution:** Use `ariaLabel` prop on Button component.

### Issue: List items not keyboard navigable
**Solution:** Use List component with `selectable={true}` which adds proper keyboard support.

## Continuous Improvement

This is a living document. As we discover new accessibility patterns or issues:
1. Document them here
2. Update components as needed
3. Add tests to prevent regressions
4. Share knowledge with the team
