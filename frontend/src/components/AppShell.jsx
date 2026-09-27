/**
 * Page frame: header, AI disclaimer, and main content.
 * @param {{userMenu?: React.ReactNode, badge?: string,
 *     children: React.ReactNode}} props
 */
export default function AppShell({ userMenu, badge, children }) {
  return (
    <div className="app">
      <header className="app__header">
        <div className="brand">
          <span className="brand__mark" aria-hidden="true">◈</span>
          <span className="brand__name">CourseCompass</span>
          {badge && <span className="badge">{badge}</span>}
        </div>
        {userMenu}
      </header>
      <p className="disclaimer">
        CourseCompass uses AI and can make mistakes. Double-check important
        details with your advisor.
      </p>
      <main className="app__main">{children}</main>
    </div>
  );
}
