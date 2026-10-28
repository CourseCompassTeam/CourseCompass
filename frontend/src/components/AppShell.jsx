/**
 * Page frame: header, AI disclaimer, and main content.
 * @param {{actions?: React.ReactNode, userMenu?: React.ReactNode,
 *     badge?: string, children: React.ReactNode}} props
 */
export default function AppShell({ actions, userMenu, badge, children }) {
  return (
    <div className="app">
      <header className="app__header">
        <div className="brand">
          <span className="brand__mark" aria-hidden="true">◈</span>
          <span className="brand__name">CourseCompass</span>
          {badge && <span className="badge">{badge}</span>}
        </div>
        {(actions || userMenu) && (
          <div className="app__actions">
            {actions}
            {userMenu}
          </div>
        )}
      </header>
      <p className="disclaimer">
        CourseCompass uses AI and can make mistakes. Double-check important
        details with your advisor.
      </p>
      <main className="app__main">{children}</main>
    </div>
  );
}
