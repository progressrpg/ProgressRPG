import React, { useState } from 'react';
import Form from '../Form/Form';
import useWaitlistJoin from '../../hooks/useWaitlistJoin';
import styles from './WaitlistForm.module.scss';

export default function WaitlistForm({ title = 'Join the Waitlist' }: { title?: string }) {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [confirmationMessage, setConfirmationMessage] = useState('');
  const { joinWaitlist } = useWaitlistJoin();

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    const result = await joinWaitlist(email);

    setIsSubmitting(false);

    if (result.success) {
      setEmail('');
      setConfirmationMessage(result.message);
    } else {
      setError(result.errorMessage);
    }
  };

  if (confirmationMessage) {
    return <p className={styles.confirmation}>{confirmationMessage}</p>;
  }

  return (
    <>
      <Form
        title={title}
        fields={[
          {
            name: 'email',
            label: 'Email:',
            type: 'email',
            placeholder: 'Email',
            autoComplete: 'email',
            value: email,
            onChange: (value) => setEmail(value as string),
            required: true,
          },
        ]}
        onSubmit={handleSubmit}
        submitLabel="Join Waitlist"
        isSubmitting={isSubmitting}
      />
      {error && <p className={styles.error} role="alert">{error}</p>}
    </>
  );
}
