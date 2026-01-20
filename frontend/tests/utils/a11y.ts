import { Page, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

export async function checkA11y(
  page: Page,
  options?: {
    exclude?: string[];
    include?: string[];
    disableRules?: string[];
  }
) {
  const builder = new AxeBuilder({ page });

  if (options?.exclude) {
    builder.exclude(options.exclude);
  }

  if (options?.include) {
    builder.include(options.include);
  }

  if (options?.disableRules) {
    builder.disableRules(options.disableRules);
  }

  const results = await builder.analyze();

  return results;
}

export function expectNoA11yViolations(results: any) {
  if (results.violations.length > 0) {
    console.error('Accessibility violations found:');
    results.violations.forEach((violation: any) => {
      console.error(`- ${violation.id}: ${violation.description}`);
      console.error(`  Help: ${violation.helpUrl}`);
      violation.nodes.forEach((node: any) => {
        console.error(`  Element: ${node.html}`);
      });
    });
  }
  
  expect(results.violations).toHaveLength(0);
}
