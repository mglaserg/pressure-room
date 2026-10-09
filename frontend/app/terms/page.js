export const metadata = {
  title: 'Terms of Service · Pressure Room',
  description: 'Terms governing Pressure Room story-development and screenwriting.',
};
export default function TermsOfService() {
  return <main className="legal-page">
    <a className="legal-back" href="/">← Pressure Room</a>
    <div className="legal-eyebrow">Legal</div><h1>Terms of Service</h1>
    <p className="legal-updated">Updated October 9, 2026</p>
    <p className="legal-lede">These terms govern use of Pressure Room, a story-development and screenwriting workspace.</p>
    <section className="legal-section"><h2>Service</h2><p>Pressure Room provides tools for developing stories, scenes, characters, screenplay text and related creative material. Features may be changed or discontinued.</p></section>
    <section className="legal-section"><h2>Accounts and storage</h2><p>Cloud accounts use Supabase email authentication and Supabase Postgres for project storage. Browser-local stories stay on the device. You are responsible for protecting your account session and retaining any independent backups you consider necessary.</p></section>
    <section className="legal-section"><h2>Your content</h2><p>You retain ownership of content you create or upload. You grant permission only as needed to process, store and share your material through the features you request.</p></section>
    <section className="legal-section"><h2>Use and access</h2><p>Do not violate applicable law, infringe others&apos; rights, access another user&apos;s data without authorization, or interfere with application security. Project owners control invitations and collaborator permissions.</p></section>
    <section className="legal-section"><h2>Availability and third parties</h2><p>Pressure Room depends on third-party infrastructure including Supabase and Amazon Web Services. The service may be interrupted or unavailable. Use is provided on an &quot;as is&quot; basis to the extent permitted by applicable law.</p></section>
    <section className="legal-section"><h2>Backups and data loss</h2><p>Keep portable backup copies when necessary. Data loss may result from software defects, deletion, service incidents or device failures. The service does not promise uninterrupted access or absolute data security.</p></section>
    <section className="legal-section"><h2>Changes and contact</h2><p>These terms may be updated as the service evolves. Contact the application operator for questions about the service.</p></section>
  </main>;
}
