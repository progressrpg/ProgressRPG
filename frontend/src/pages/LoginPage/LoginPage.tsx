import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router';
import useLogin from '../../hooks/useLogin';
import { useAuth } from '../../context/AuthContext';
import Form from '../../components/Form/Form';
import Input from '../../components/Input/Input';
import styles from './LoginPage.module.scss';

export default function LoginPage(): React.ReactElement {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const loginWithJwt = useLogin();
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');

    const result1 = await loginWithJwt(email, password, rememberMe);
    //console.log('LoginPage login result1:', result1);

    if (result1.success) {
      try {
        await login(result1.tokens.access_token, result1.tokens.refresh_token, { rememberMe });
        navigate('/');

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
        frameClass={styles.formFrame}
        className={styles.form}
      >
        {error && <p className={styles.error} role="alert">{error}</p>}
        <Input
          id="email"
          type="email"
          placeholder="Email"
          autoComplete='email'
          value={email}
          onChange={(v) => setEmail(v as string)}
          required
        />
        <Input
          id="password"
          type="password"
          placeholder="Password"
          autoComplete='current-password'
          value={password}
          onChange={(v) => setPassword(v as string)}
          required
        />
        <Input
          id="remember-me"
          type="checkbox"
          label="Remember me"
          checked={rememberMe}
          onChange={(v) => setRememberMe(v as boolean)}
          className={styles.rememberMeField}
          inputClassName={styles.rememberMeInput}
        />
        <p className={styles.footer}>
          New here? <Link to="/register">Create an account</Link>
        </p>
        <p className={styles.footer}>
          <Link to="/forgot-password">Forgot your password?</Link>
        </p>
      </Form>
    </div>
  );
}
