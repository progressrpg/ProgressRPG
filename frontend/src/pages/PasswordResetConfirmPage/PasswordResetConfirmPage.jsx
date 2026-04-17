import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import Form from '../../components/Form/Form';
import usePasswordReset from '../../hooks/usePasswordReset';
import styles from '../PasswordResetPage.module.scss';

function parseResetKey(key) {
  const separatorIndex = key.indexOf('-');

  if (separatorIndex <= 0 || separatorIndex === key.length - 1) {
    return null;
  }

  return {
    uid: key.slice(0, separatorIndex),
    token: key.slice(separatorIndex + 1),
  };
}

export default function PasswordResetConfirmPage() {
  const { key = '' } = useParams();
  const parsedKey = useMemo(() => parseResetKey(key), [key]);
  const [password1, setPassword1] = useState('');
  const [password2, setPassword2] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState('');
  const [submittedMessage, setSubmittedMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const { confirmPasswordReset } = usePasswordReset();

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!parsedKey) {
      return;
    }

    setSubmitting(true);
    setError('');
    setFieldErrors({});

    const result = await confirmPasswordReset({
      uid: parsedKey.uid,
      token: parsedKey.token,
      password1,
      password2,
    });

    if (result.success) {
      setSubmittedMessage(result.message);
      setPassword1('');
      setPassword2('');
    } else {
      setError(result.errorMessage);
      setFieldErrors(result.errors || {});
    }

    setSubmitting(false);
  };

  if (!parsedKey) {
    return (
      <div className={styles.page}>
        <div className={styles.panel}>
          <h1 className={styles.title}>Invalid reset link</h1>
          <p className={styles.body}>
            This password reset link is invalid or incomplete.
          </p>
          <p className={styles.footer}>
            <Link to="/forgot-password">Contact support for a reset</Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      {submittedMessage ? (
        <div className={styles.panel}>
          <h1 className={styles.title}>Password updated</h1>
          <p className={styles.body}>{submittedMessage}</p>
          <p className={styles.footer}>
            <Link to="/login">Log in</Link>
          </p>
        </div>
      ) : (
        <Form
          title="Choose a new password"
          onSubmit={handleSubmit}
          fields={[
            {
              name: 'new_password1',
              label: 'New password:',
              type: 'password',
              placeholder: 'New password',
              autoComplete: 'new-password',
              value: password1,
              onChange: setPassword1,
              required: true,
            },
            {
              name: 'new_password2',
              label: 'Confirm new password:',
              type: 'password',
              placeholder: 'Confirm new password',
              autoComplete: 'new-password',
              value: password2,
              onChange: setPassword2,
              required: true,
            },
          ]}
          isSubmitting={submitting}
          submitLabel="Update password"
          className={styles.form}
          fieldErrors={fieldErrors}
        >
          {error && (
            <p className={styles.error} role="alert">
              {error}
            </p>
          )}
          <p className={styles.footer}>
            <Link to="/login">Back to login</Link>
          </p>
        </Form>
      )}
    </div>
  );
}
