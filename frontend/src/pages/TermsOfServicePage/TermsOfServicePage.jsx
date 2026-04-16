import { Link } from 'react-router-dom';
import styles from '../LegalPage/LegalPage.module.scss';
import BackToTopButton from '../../components/BackToTopButton/BackToTopButton';

const contactEmail = 'support@progressrpg.com';

function getSectionId(title) {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '');
}

const sections = [
  {
    title: 'Scope of These Terms',
    body: [
      'These Terms apply to your use of ProgressRPG.com, the Progress RPG app, and any other related products or services provided by me. By accessing or using any part of the Services, you agree to be bound by these Terms.',
      'If you access the Services from outside the United Kingdom, you are responsible for complying with local laws.',
      'If you do not agree, please do not use the Services.',
    ],
  },
  {
    title: '1. About the Services',
    body: [
      'I provide the Services from England. If you access them from outside the UK, you are responsible for following your local laws.',
      'The Services are not designed for regulated industries such as healthcare or finance, so please do not use them for those purposes.',
    ],
  },
  {
    title: '2. Intellectual Property',
    body: [
      'All content on the Services, including code, designs, text, images, and logos, belongs to me or my licensors. You may use the Services and view or print content for your personal, non-commercial use only.',
      'You must not copy, reproduce, distribute, or exploit any part of the Services for commercial purposes without my written permission.',
    ],
  },
  {
    title: '3. Your Contributions',
    body: [
      'If you send me feedback, suggestions, or content, you keep ownership, but you allow me to use and share your Contributions to run and improve the Services.',
      'You are responsible for your Contributions and must not submit anything illegal, offensive, or that infringes anyone else’s rights.',
    ],
  },
  {
    title: '4. User Accounts',
    body: [
      'You may need to register for an account to use some features. Please keep your password safe and let me know if you suspect unauthorised use.',
      'I may remove or change usernames that are inappropriate.',
    ],
  },
  {
    title: '5. Products and Purchases',
    body: [
      'All products and subscriptions are subject to availability and may change at any time. Prices are in GBP and may change.',
      'I accept payment by Mastercard, Visa, and PayPal. Payments are processed securely by third-party providers; I do not store your card details.',
      'You agree to provide accurate payment details and to pay any charges for your purchases.',
    ],
  },
  {
    title: '6. Subscriptions',
    body: [
      'If you buy a subscription, it will renew automatically unless you cancel. You can cancel at any time in your account settings, and cancellation takes effect at the end of the current paid period.',
      'If subscription prices change, I will let you know in advance.',
    ],
  },
  {
    title: '7. Refunds',
    body: ['All sales are final. I do not offer refunds unless required by law.'],
  },
  {
    title: '8. Prohibited Activities',
    body: ['You must not:'],
    bullets: [
      'Use the Services for unlawful or harmful purposes.',
      'Attempt to gain unauthorised access to the Services or other users’ accounts.',
      'Upload viruses, malware, or harmful content.',
      'Harass, abuse, or harm others.',
      'Use automated tools such as bots or scrapers to access the Services.',
      'Copy, adapt, reverse engineer, or create derivative works from the software, except as allowed by law.',
      'Interfere with the operation or security of the Services.',
      'Sell or transfer your account to anyone else.',
      'Use the Services for commercial purposes without my permission.',
    ],
  },
  {
    title: '9. User-Generated Content',
    body: ['If you are able to submit content such as text, images, or other materials, you confirm that:'],
    bullets: [
      'You own or have permission to use the content.',
      'Your content does not infringe anyone else’s rights or break any law.',
      'Your content is not offensive, abusive, defamatory, or otherwise inappropriate.',
      'Your content does not contain personal data of others without their consent.',
    ],
  },
  {
    title: '10. Contribution Licence',
    body: [
      'By submitting content or feedback, you allow me to use, display, and share it as needed to operate and improve the Services.',
      'You keep ownership of your content, but you are responsible for it.',
    ],
  },
  {
    title: '11. Social Media and Third-Party Accounts',
    body: [
      'If you link your account with a social media or third-party service, you confirm you have the right to do so.',
      'I may access and display certain information from that account, such as your username or profile picture, depending on your settings.',
      'You can disconnect third-party accounts at any time in your settings or by contacting me.',
      'Your relationship with third-party services is governed by your agreement with them.',
    ],
  },
  {
    title: '12. Service Management',
    body: ['I may:'],
    bullets: [
      'Monitor the Services for breaches of these Terms.',
      'Remove or restrict access to content that breaches these Terms or is otherwise inappropriate.',
      'Take action against users who break the law or these Terms, including reporting to authorities.',
      'Remove large or disruptive files to keep the Services running smoothly.',
    ],
  },
  {
    title: '13. Privacy',
    body: [
      'I take your privacy seriously. Please read the Privacy Policy to understand how your data is collected, used, and protected.',
      'The Services are hosted in the UK. If you use them from outside the UK, your data may be transferred to and processed in the UK.',
    ],
  },
  {
    title: '14. Termination',
    body: [
      'I may suspend or terminate your access to the Services if you breach these Terms or if required by law. Where possible, I will give you notice. You can stop using the Services at any time.',
    ],
  },
  {
    title: '15. Changes to These Terms',
    body: [
      'I may update these Terms from time to time. If I make significant changes, I will notify you by email or through the Services. The updated Terms take effect when posted. By continuing to use the Services, you agree to the updated Terms.',
    ],
  },
  {
    title: '16. Disclaimer',
    body: [
      'The Services are provided “as is” and “as available.” I do not guarantee that the Services will always be available or error-free. Nothing in these Terms limits or excludes my liability for death, personal injury caused by my negligence, or fraud.',
    ],
  },
  {
    title: '17. Limitation of Liability',
    body: [
      'If I fail to comply with these Terms, I am responsible for foreseeable loss or damage you suffer as a result. I am not liable for loss or damage that is not foreseeable.',
      'Nothing in these Terms excludes liability where it would be unlawful to do so.',
    ],
  },
  {
    title: '18. Your Rights',
    body: [
      'You have rights under UK law, including to access, correct, or delete your personal data. For details, please see the Privacy Policy or contact me.',
    ],
  },
  {
    title: '19. Governing Law',
    body: [
      'These Terms are governed by the laws of England and Wales. Any disputes will be resolved in the courts of England and Wales.',
    ],
  },
  {
    title: '20. Contact',
    body: [
      `If you have any questions about these Terms, please email ${contactEmail}.`,
      'We recommend you print or save a copy of these Terms for your records.',
    ],
  },
];

export default function TermsOfServicePage() {
  return (
    <main id="legal-page-top" className={styles.page}>
      <article className={styles.card}>
        <header className={styles.header}>
          <h1 className={styles.title}>Terms of Service</h1>
          <p className={styles.effectiveDate}>Effective date: 8th June</p>
          <p className={styles.lead}>Welcome to Progress RPG.</p>
          <p className={styles.lead}>
            If you have any questions, contact me at{' '}
            <a className={styles.contactLink} href={`mailto:${contactEmail}`}>{contactEmail}</a>.
          </p>
        </header>

        <nav className={styles.toc} aria-labelledby="terms-of-service-toc">
          <h2 id="terms-of-service-toc" className={styles.tocTitle}>Contents</h2>
          <ul className={styles.tocList}>
            {sections.map((section) => (
              <li key={section.title}>
                <a href={`#${getSectionId(section.title)}`}>{section.title}</a>
              </li>
            ))}
          </ul>
        </nav>

        <div className={styles.content}>
          {sections.map((section) => (
            <section
              key={section.title}
              aria-labelledby={getSectionId(section.title)}
              className={styles.section}
            >
              <h2 id={getSectionId(section.title)} className={styles.sectionTitle} tabIndex="-1">
                {section.title}
              </h2>
              {section.body?.map((paragraph) => (
                <p key={paragraph}>
                  {paragraph.includes('Privacy Policy') ? (
                    <>
                      I take your privacy seriously. Please read the{' '}
                      <Link to="/privacy-policy">Privacy Policy</Link> to understand how your
                      data is collected, used, and protected.
                    </>
                  ) : paragraph.includes('please see the Privacy Policy') ? (
                    <>
                      You have rights under UK law, including to access, correct, or delete
                      your personal data. For details, please see the{' '}
                      <Link to="/privacy-policy">Privacy Policy</Link> or contact me.
                    </>
                  ) : (
                    paragraph
                  )}
                </p>
              ))}
              {section.bullets && (
                <ul>
                  {section.bullets.map((bullet) => (
                    <li key={bullet}>{bullet}</li>
                  ))}
                </ul>
              )}
            </section>
          ))}
        </div>
      </article>
      <BackToTopButton />
    </main>
  );
}
