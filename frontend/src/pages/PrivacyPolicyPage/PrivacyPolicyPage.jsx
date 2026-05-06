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
    title: '1. What Information I Collect',
    body: [
      'Depending on how you use the Services, I may collect:',
    ],
    bullets: [
      'Contact details, such as your email address if you register or contact me.',
      'Account information, such as your username and password.',
      'Payment information if you make purchases or subscribe. Payments are processed securely by third-party providers, and I do not store your card details.',
      'Usage data, such as your IP address, browser type, and how you use the Services, collected via cookies and analytics tools.',
      'Any information you choose to provide, such as feedback or support requests.',
    ],
  },
  {
    title: '2. How I Use Your Information',
    bullets: [
      'Provide, maintain, and improve the Services.',
      'Create and manage your account.',
      'Process payments and subscriptions.',
      'Communicate with you, including updates, support, or important changes.',
      'Ensure the security and integrity of the Services.',
      'Comply with legal obligations.',
    ],
    body: ['I do not use your information for profiling or automated decision-making.'],
  },
  {
    title: '3. Sharing Your Information',
    bullets: [
      'With trusted third-party service providers, such as payment processors or hosting providers, only as needed to run the Services.',
      'If required by law, regulation, or to protect rights and safety.',
      'If I sell or transfer the Services in the future, you will be notified and your data will be protected.',
    ],
    body: ['I do not sell your personal information to anyone.'],
  },
  {
    title: '4. International Transfers',
    body: [
      'Your information is stored and processed in the United Kingdom. If you use the Services from outside the UK, your data may be transferred to and processed in the UK. By using the Services, you consent to this.',
    ],
  },
  {
    title: '5. How I Protect Your Information',
    body: [
      'I use reasonable technical and organisational measures to protect your information from unauthorised access, loss, or misuse. However, no online service can be completely secure, so please keep your password safe and contact me if you believe your account has been compromised.',
    ],
  },
  {
    title: '6. How Long I Keep Your Information',
    body: [
      'I keep your information only as long as needed to provide the Services, comply with legal requirements, or resolve disputes. If you close your account, I will delete your personal information unless I need to keep it for legal reasons.',
    ],
  },
  {
    title: '7. Your Rights',
    body: ['Under UK data protection law, you have the right to:'],
    bullets: [
      'Access the personal information I hold about you.',
      'Ask me to correct or delete your personal information.',
      'Object to or restrict how I use your information.',
      'Withdraw your consent if I rely on consent.',
      'Complain to the UK Information Commissioner’s Office (ICO) if you are unhappy with how I handle your data.',
    ],
  },
  {
    title: '8. Children’s Privacy',
    body: [
      'The Services are intended for users aged 18 or over. I do not knowingly collect personal information from children under 18. If you believe I have collected information from a child, please contact me so I can remove it.',
    ],
  },
  {
    title: '9. Changes to This Policy',
    body: [
      'I may update this Privacy Policy from time to time. If I make significant changes, I will notify you by email or through the Services. The updated policy will take effect when posted.',
    ],
  },
  {
    title: '10. Contact',
    body: [
      `If you have any questions about this Privacy Policy or your personal information, please contact me at ${contactEmail}.`,
      'We recommend you print or save a copy of this policy for your records.',
    ],
  },
];

export default function PrivacyPolicyPage() {
  return (
    <div id="legal-page-top" className={styles.page}>
      <article className={styles.card}>
        <header className={styles.header}>
          <h1 className={styles.title}>Privacy Policy</h1>
          <p className={styles.effectiveDate}>Effective date: 8th June 2025</p>
          <p className={styles.lead}>
            Welcome to Progress RPG.
          </p>
          <p className={styles.lead}>
            This Privacy Policy explains how I collect, use, store, and protect your
            personal information when you use ProgressRPG.com, the Progress RPG app,
            and any related products or services. I am based in England and operate as
            an individual developer.
          </p>
          <p className={styles.lead}>
            If you have any questions, please contact me at{' '}
            <a className={styles.contactLink} href={`mailto:${contactEmail}`}>{contactEmail}</a>.
          </p>
        </header>

        <nav className={styles.toc} aria-labelledby="privacy-policy-toc">
          <h2 id="privacy-policy-toc" className={styles.tocTitle}>Contents</h2>
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
                <p key={paragraph}>{paragraph}</p>
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
    </div>
  );
}
