// Temporary: password reset is handled manually via support while transactional
// emails are not yet operational. Replace with the standard reset flow once email
// is working.
import { useState } from 'react';
import styles from '../LoginPage/LoginPage.module.scss';
import Form from '../../components/Form/Form';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    const subject = encodeURIComponent('Password reset request');
    const body = encodeURIComponent(
      `Hi Support,\n\nPlease reset the password for my account: ${email}\n\nThanks`
    );
    window.location.href = `mailto:support@progressrpg.com?subject=${subject}&body=${body}`;
  };

  return (
    <div className={styles.page}>
      <Form
        title="🔑 Forgot Password"
        onSubmit={handleSubmit}
        submitLabel="Email Support"
      >
        <p>
          Automated password resets are temporarily unavailable while we set up
          transactional email. To reset your password, enter your email address
          below and click <strong>Email Support</strong>. This will open your
          email client with a pre-filled message to{' '}
          <a href="mailto:support@progressrpg.com">support@progressrpg.com</a>.
        </p>
        <label htmlFor="forgot-password-email">Email address</label>
        <input
          id="forgot-password-email"
          type="email"
          name="email"
          placeholder="Your account email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
      </Form>
    </div>
  );
}
