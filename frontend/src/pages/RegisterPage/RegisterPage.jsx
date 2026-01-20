import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import Form from '../../components/Form/Form';
import useRegister from '../../hooks/useRegister';

export default function RegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const navigate = useNavigate();
  const { register, characterAvailable } = useRegister();
  const [inviteCode, setInviteCode] = useState('');
  const [agreeToTerms, setAgreeToTerms] = useState(false);
  const location = useLocation();
  const [formState, setFormState] = useState("default");

  useEffect(() => {
    // Reset form or state when location changes (even to the same path)
    setFormState("default");
  }, [location.key]); // `key` changes on every navigation

  const handleRegister = async e => {
    e.preventDefault();
    setError('');
    setFieldErrors({});

    if (password !== confirmPassword) {
      setError("Passwords don't match");
      return;
    }

    const { success, errors, errorMessage, confirmationRequired } = await register(
      email,
      password,
      confirmPassword,
      inviteCode,
      agreeToTerms
    );

    if (success) {
      setEmail('');
      setPassword('');
      setConfirmPassword('');
      setInviteCode('');
      setAgreeToTerms(false);

      if (confirmationRequired) {
        setFormState("submitted");
      } else {
        navigate('/game');
      }
    } else {
      setError(errorMessage);
      setFieldErrors(errors || {});
    }
  };

  return (
    <div>
      {formState === "submitted" ? (
        <div>
          <p>
            Thanks for registering! Please check your email and follow the confirmation link before logging in.
          </p>
          {!characterAvailable && <p>We don't currently have any characters available for you to link with! Please still confirm your email, and we will let you know as soon as a character becomes available.</p>}
        </div>
      ) : (
        <Form
          title="📝 Register"
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
            {
              name: 'password',
              label: 'Password:',
              type: 'password',
              placeholder: 'Password',
              autoComplete: 'new-password',
              value: password,
              onChange: setPassword,
              required: true,
            },
            {
              name: 'confirmPassword',
              label: 'Confirm password:',
              type: 'password',
              placeholder: 'Confirm Password',
              autoComplete: 'new-password',
              value: confirmPassword,
              onChange: setConfirmPassword,
              required: true,
            },
            {
              name: 'invite_code',
              label: 'Invite Code:',
              type: 'text',
              placeholder: 'e.g. TESTER',
              value: inviteCode,
              onChange: setInviteCode,
              required: true,
            },
            {
              name: 'agree_to_terms',
              label: (
                <>
                  I agree to the{' '}
                  <a href="https://progressrpg.com/terms-of-service/" target='_blank' rel='noopener noreferrer'>
                    Terms of Service
                  </a>{' '}
                  and{' '}
                  <a href="https://progressrpg.com/privacy-policy-2/" target='_blank' rel='noopener noreferrer'>
                    Privacy Policy
                  </a>
                  .
                </>
              ),
              type: 'checkbox',
              checked: agreeToTerms,
              onChange: e => setAgreeToTerms(e.target.checked),
              required: true,
            },
          ]}
          error={error}
          onSubmit={handleRegister}
          submitLabel="Create Account"
          fieldErrors={fieldErrors}
        />
      )}
      {error && <p className="error" role="alert">{error}</p>}
    </div>
  );
}
