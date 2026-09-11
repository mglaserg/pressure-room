export const metadata = {
  title: 'Privacy Policy · Pressure Room',
  description: 'Privacy practices for Pressure Room, including Google Drive access and storage.',
};

export default function PrivacyPolicy() {
  return (
    <main className="legal-page">
      <a className="legal-back" href="/">← Pressure Room</a>
      <div className="legal-eyebrow">Legal</div>
      <h1>Privacy Policy</h1>
      <p className="legal-updated">Effective September 11, 2026</p>

      <p className="legal-lede">
        Pressure Room is a story-development and screenwriting workspace. This Privacy Policy explains
        what information Pressure Room accesses, how it is used, and the choices available to you,
        including when you connect your Google Drive.
      </p>

      <section className="legal-section">
        <h2>1. Information Pressure Room accesses</h2>
        <p>When you connect a Google account, Pressure Room may receive:</p>
        <ul>
          <li>Your Google account email address and stable account identifier.</li>
          <li>OAuth access and refresh credentials needed to maintain your authorized Drive connection.</li>
          <li>Google Drive file metadata and file contents for files Pressure Room creates or files you explicitly make available to Pressure Room.</li>
        </ul>
        <p>
          Pressure Room requests the Google Drive <code>drive.file</code> scope. It does not request
          general access to browse the contents of your entire Google Drive.
        </p>
      </section>

      <section className="legal-section">
        <h2>2. How Google user data is used</h2>
        <p>Google user data is used only to provide Pressure Room features, including:</p>
        <ul>
          <li>Identifying the Google account connected to the current session.</li>
          <li>Creating or locating the Pressure Room folder available to the app.</li>
          <li>Saving, loading, and synchronizing your Pressure Room project files.</li>
          <li>Maintaining your Drive authorization between sessions.</li>
        </ul>
        <p>
          Pressure Room does not sell Google user data and does not use Google user data for advertising,
          ad targeting, or unrelated profiling.
        </p>
      </section>

      <section className="legal-section">
        <h2>3. Where your story data is stored</h2>
        <p>
          When Google Drive storage is enabled, your Pressure Room project files are stored in your own
          Google Drive and remain under your Google account.
        </p>
        <p>
          Pressure Room may create a temporary, user-isolated SQLite cache on its application server so
          the workspace can operate efficiently. This cache is not intended to be the canonical copy of
          your work. Temporary server caches are removed as application compute is recycled.
        </p>
      </section>

      <section className="legal-section">
        <h2>4. Authentication and session data</h2>
        <p>
          Pressure Room stores the Google authorization session in an encrypted, HttpOnly cookie. The
          cookie may contain your Google account identifier, email address, OAuth tokens, and token expiry
          information. Access tokens may also be cached temporarily in application memory.
        </p>
        <p>Session credentials are used only to provide the Drive connection you authorized.</p>
      </section>

      <section className="legal-section">
        <h2>5. Sharing and service providers</h2>
        <p>
          Pressure Room uses service providers necessary to operate the application, including Google for
          OAuth and Google Drive functionality and Amazon Web Services for application hosting.
          Information may be processed by those providers as necessary to deliver the service.
        </p>
        <p>
          Pressure Room does not sell or rent your personal information. Information may also be disclosed
          when required by law or when reasonably necessary to protect the security, rights, or integrity
          of Pressure Room or its users.
        </p>
      </section>

      <section className="legal-section">
        <h2>6. Google API Limited Use</h2>
        <p>
          Pressure Room&apos;s use and transfer of information received from Google APIs will adhere to the{' '}
          <a href="https://developers.google.com/terms/api-services-user-data-policy" target="_blank" rel="noreferrer">
            Google API Services User Data Policy
          </a>
          , including the Limited Use requirements.
        </p>
      </section>

      <section className="legal-section">
        <h2>7. Retention and your choices</h2>
        <p>
          Your Pressure Room project files remain in your Google Drive until you delete them. Disconnecting
          Google Drive from Pressure Room removes the local browser session but does not delete your Drive files.
        </p>
        <p>
          You can revoke Pressure Room&apos;s Google access at any time from your Google Account&apos;s
          third-party access controls. You can also delete the Pressure Room files or folder from your Drive.
        </p>
      </section>

      <section className="legal-section">
        <h2>8. Security</h2>
        <p>
          Pressure Room uses reasonable technical safeguards appropriate to the service, including HTTPS,
          encrypted session cookies, scoped Google OAuth access, and managed secret storage. No method of
          transmission or storage is completely secure, so absolute security cannot be guaranteed.
        </p>
      </section>

      <section className="legal-section">
        <h2>9. Children</h2>
        <p>
          Pressure Room is not directed to children under 13, and it is not intended to knowingly collect
          personal information from children under 13.
        </p>
      </section>

      <section className="legal-section">
        <h2>10. Changes to this policy</h2>
        <p>
          This policy may be updated as Pressure Room changes. The effective date at the top of this page
          will be updated when material changes are made.
        </p>
      </section>

      <section className="legal-section">
        <h2>11. Contact</h2>
        <p>
          For privacy questions, contact the developer using the support email listed for Pressure Room on
          its Google OAuth consent screen.
        </p>
      </section>

      <div className="legal-note">
        Pressure Room is designed around a simple storage principle: your stories live in your Drive, and
        the app requests only the Google access needed to work with Pressure Room files.
      </div>
    </main>
  );
}
