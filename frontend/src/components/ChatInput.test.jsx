import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import AppShell from './AppShell.jsx';
import ChatInput from './ChatInput.jsx';
import { ScheduleButton } from './schedule/ScheduleDialog.jsx';

describe('ChatInput', () => {
  it('renders an empty, disabled send button', () => {
    const html = renderToStaticMarkup(<ChatInput onSubmit={() => {}} disabled={false} />);

    expect(html).toContain('placeholder="Ask a question…"');
    expect(html).toContain('disabled=""');
    expect(html).toContain('>Send<');
  });
});

describe('AppShell', () => {
  it('renders the brand, badge, actions and page content', () => {
    const html = renderToStaticMarkup(
      <AppShell badge="Dev" actions={<span>Reset</span>} userMenu={<span>Menu</span>}>
        <p>Page body</p>
      </AppShell>,
    );

    expect(html).toContain('CourseCompass');
    expect(html).toContain('>Dev<');
    expect(html).toContain('Reset');
    expect(html).toContain('Menu');
    expect(html).toContain('Page body');
    expect(html).toContain('AI and can make mistakes');
  });

  it('omits the action area when there are no actions', () => {
    const html = renderToStaticMarkup(<AppShell><p>x</p></AppShell>);

    expect(html).not.toContain('app__actions');
  });
});

describe('ScheduleButton', () => {
  it('renders a labelled Schedule button that starts closed', () => {
    const html = renderToStaticMarkup(<ScheduleButton scheduleService={{}} />);

    expect(html).toContain('aria-label="Schedule"');
    expect(html).toContain('>Schedule<');
  });
});
