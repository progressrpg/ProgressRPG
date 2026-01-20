import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useLogin from '../../hooks/useLogin';
import { useAuth } from '../../context/AuthContext';
import Form from '../../components/Form/Form';
import styles from './LoginPage.module.scss';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const loginWithJwt = useLogin();
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');

    const result1 = await loginWithJwt(email, password);
    //console.log('LoginPage login result1:', result1);

    if (result1.success) {
      try {
        const result2 = await login(result1.tokens.access_token, result1.tokens.refresh_token);
        //console.log('[HANDLE SUBMIT] result2:', result2);
        if (result2.onboarding_step && result2.onboarding_step < 4) {
          navigate('/onboarding');
        } else {
          navigate('/game');
        }

      } catch (err) {
        setError("Login succeeded but failed to fetch user info.");
        console.error('Post-login user fetch failed:', err);
      }
    } else {
      setError(result1.error || 'Login failed');
    }

    setSubmitting(false);
  };

  return (
    <div className={styles.page}>
      <Form
        title="🔐 Log in"
        onSubmit={handleSubmit}
        isSubmitting={submitting}
        submitLabel="Log In"
        className={styles.form}
      >
        {error && <p className={styles.error} role="alert">{error}</p>}
        <input
          type="email"
          name="email"
          placeholder="Email"
          autoComplete='email'
          value={email}
          onChange={e => setEmail(e.target.value)}
          required
        />
        <input
          type="password"
          name="password"
          placeholder="Password"
          autoComplete='current-password'
          value={password}
          onChange={e => setPassword(e.target.value)}
          required
        />
        <p className={styles.footer}>
          New here? <a href="/register">Create an account</a>
        </p>
      </Form>
    </div>
  );
}
