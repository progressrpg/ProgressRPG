import { useState } from 'react';
import { Link } from 'react-router-dom';
import Form from '../../components/Form/Form';
import usePasswordReset from '../../hooks/usePasswordReset';
import styles from '../PasswordResetPage.module.scss';

export default function PasswordResetRequestPage() {
  const [email, setEmail] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState('');
  const [submittedMessage, setSubmittedMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const { requestPasswordReset } = usePasswordReset();

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    setFieldErrors({});

    const result = await requestPasswordReset(email);

    if (result.success) {
      setSubmittedMessage(result.message);
      setEmail('');
    } else {
      setError(result.errorMessage);
      setFieldErrors(result.errors || {});
    }

    setSubmitting(false);
  };

  return (
    <div className={styles.page}>
      {submittedMessage ? (
        <div className={styles.panel}>
          <h1 className={styles.title}>Check your email</h1>
          <p className={styles.body}>{submittedMessage}</p>
          <p className={styles.footer}>
            <Link to="/login">Back to login</Link>
          </p>
        </div>
      ) : (
        <Form
          title="Reset your password"
          onSubmit={handleSubmit}
          fields={[
            {
              name: 'email',
              label: 'Email:',
              type: 'email',
              placeholder: 'Email',
              autoComplete: 'email',
              value: email,
              onChange: setEmail,
              required: true,
            },
          ]}
          isSubmitting={submitting}
          submitLabel="Send reset link"
          className={styles.form}
          fieldErrors={fieldErrors}
        >
          {error && (
            <p className={styles.error} role="alert">
              {error}
            </p>
          )}
          <p className={styles.footer}>
            Remembered it? <Link to="/login">Log in</Link>
          </p>
        </Form>
      )}
    </div>
  );
}
