export const metadata = {
  title: 'Privacy Policy · Pressure Room',
  description: 'Privacy practices for Pressure Room story storage and authentication.',
};
export default function PrivacyPolicy() {
  return <main className="legal-page">
    <a className="legal-back" href="/">← Pressure Room</a>
    <div className="legal-eyebrow">Legal</div><h1>Privacy Policy</h1>
    <p className="legal-updated">Updated October 9, 2026</p>
    <p className="legal-lede">Pressure Room is a story-development and screenwriting workspace. This policy explains the data used to provide the service.</p>
    <section className="legal-section"><h2>Information we process</h2><p>When you sign in, we process the email address and account identity needed to authenticate you. We process the stories, screenplay text, scene notes, project membership, and related material you choose to save in your cloud workspace.</p></section>
    <section className="legal-section"><h2>Storage</h2><p>Cloud projects and project access are held in Supabase Postgres. The backend may keep a separate, temporary SQLite working cache for an authenticated user. Browser-local projects remain in the local browser until you explicitly export or move them.</p></section>
    <section className="legal-section"><h2>Sessions and sharing</h2><p>Cloud sign-in uses Supabase email authentication and an encrypted HttpOnly application-session cookie. Owners may invite others with editor or viewer permissions. Your project content is shared with authorized collaborators on that project.</p></section>
    <section className="legal-section"><h2>Services and security</h2><p>Supabase provides authentication and durable data storage; Amazon Web Services hosts application infrastructure. We use HTTPS, access controls, and managed secrets as safeguards. No online service can guarantee absolute security.</p></section>
    <section className="legal-section"><h2>Retention and control</h2><p>Project owners can move projects to Trash, restore them, or permanently delete them. You can download a portable backup. Device-local storage can be cleared using browser controls. For questions about personal data or service operations, contact the app operator.</p></section>
  </main>;
}
