export const metadata = {
  title: 'Terms of Service · Pressure Room',
  description: 'Terms governing use of the Pressure Room story-development and screenwriting application.',
};

export default function TermsOfService() {
  return (
    <main className="legal-page">
      <a className="legal-back" href="/">← Pressure Room</a>
      <div className="legal-eyebrow">Legal</div>
      <h1>Terms of Service</h1>
      <p className="legal-updated">Effective September 11, 2026</p>

      <p className="legal-lede">
        These Terms of Service govern your use of Pressure Room, a story-development and screenwriting
        workspace. By using Pressure Room, you agree to these terms.
      </p>

      <section className="legal-section">
        <h2>1. The service</h2>
        <p>
          Pressure Room provides tools for developing stories, characters, scenes, structure, screenplay
          text, and related creative material. Features may change, be added, or be removed over time.
        </p>
      </section>

      <section className="legal-section">
        <h2>2. Your Google Drive connection</h2>
        <p>
          Pressure Room may allow you to connect your Google account and store Pressure Room project files
          in your Google Drive. You authorize Pressure Room to access only the Google data and Drive files
          permitted by the scopes you approve.
        </p>
        <p>
          Google services are provided by Google and are subject to Google&apos;s own terms and policies.
          You may disconnect or revoke Pressure Room&apos;s Google access at any time.
        </p>
      </section>

      <section className="legal-section">
        <h2>3. Your content</h2>
        <p>
          You retain ownership of the stories, screenplay material, notes, characters, and other content
          you create or store using Pressure Room.
        </p>
        <p>
          You grant Pressure Room only the limited permission necessary to process, cache, transmit, and
          store your content for the purpose of operating the service and the features you request.
        </p>
      </section>

      <section className="legal-section">
        <h2>4. Your responsibilities</h2>
        <p>You agree not to use Pressure Room to:</p>
        <ul>
          <li>Violate applicable law or the rights of another person.</li>
          <li>Attempt to gain unauthorized access to the service or another user&apos;s data.</li>
          <li>Disrupt, overload, probe, or interfere with the service&apos;s infrastructure or security.</li>
          <li>Upload or distribute malicious code through the service.</li>
        </ul>
        <p>
          You are responsible for the content you create and for ensuring that you have the rights needed
          to use any material you place in Pressure Room.
        </p>
      </section>

      <section className="legal-section">
        <h2>5. Availability and changes</h2>
        <p>
          Pressure Room may be changed, suspended, or discontinued at any time. Although the application
          is designed to keep canonical project files in your Google Drive when Drive storage is enabled,
          uninterrupted availability or error-free operation is not guaranteed.
        </p>
      </section>

      <section className="legal-section">
        <h2>6. Backups and data loss</h2>
        <p>
          You are responsible for maintaining any additional backups you consider necessary. Pressure Room
          is not responsible for data loss caused by third-party services, account access problems,
          deletion, corruption, software defects, or events outside the service&apos;s reasonable control.
        </p>
      </section>

      <section className="legal-section">
        <h2>7. Third-party services</h2>
        <p>
          Pressure Room relies on third-party services such as Google and Amazon Web Services. Those
          services may have their own terms, privacy practices, outages, limitations, and availability
          requirements. Pressure Room is not responsible for third-party services.
        </p>
      </section>

      <section className="legal-section">
        <h2>8. No warranties</h2>
        <p>
          Pressure Room is provided on an &quot;as is&quot; and &quot;as available&quot; basis to the
          fullest extent permitted by applicable law. No warranty is made that the service will be
          uninterrupted, secure, error-free, or suitable for any particular creative or commercial result.
        </p>
      </section>

      <section className="legal-section">
        <h2>9. Limitation of liability</h2>
        <p>
          To the fullest extent permitted by applicable law, the developer of Pressure Room will not be
          liable for indirect, incidental, special, consequential, exemplary, or punitive damages, or for
          loss of data, profits, opportunities, or business arising from your use of or inability to use
          the service.
        </p>
      </section>

      <section className="legal-section">
        <h2>10. Suspension or termination</h2>
        <p>
          Access to Pressure Room may be suspended or terminated when reasonably necessary to protect the
          service, comply with law, prevent abuse, or address a material violation of these terms.
        </p>
      </section>

      <section className="legal-section">
        <h2>11. Changes to these terms</h2>
        <p>
          These terms may be updated as Pressure Room evolves. The effective date at the top of this page
          will be updated when material changes are made. Continued use after an updated version becomes
          effective constitutes acceptance of the updated terms.
        </p>
      </section>

      <section className="legal-section">
        <h2>12. Contact</h2>
        <p>
          For questions about these terms, contact the developer using the support email listed for
          Pressure Room on its Google OAuth consent screen.
        </p>
      </section>
    </main>
  );
}
