import { useState } from 'react';
import styles from './Input.module.scss';
import classNames from 'classnames';

function EyeIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
      <circle cx="12" cy="12" r="3"/>
    </svg>
  );
}

function EyeOffIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/>
      <line x1="1" y1="1" x2="23" y2="23"/>
    </svg>
  );
}

export default function Input({
  id,
  label,
  type = 'text',
  value,
  onChange,
  placeholder = '',
  helpText = '',
  error = '',
  required = false,
  autoComplete,
  checked,
  minLength,
  maxLength,
  className,
  inputClassName,
  disabled = false,
  onBlur,
  onKeyDown,
}) {
  const [showPassword, setShowPassword] = useState(false);
  const isCheckbox = type === 'checkbox';
  const isPassword = type === 'password';
  const resolvedType = isPassword && showPassword ? 'text' : type;

  const helpTextId = helpText ? `${id}-help` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [helpTextId, errorId].filter(Boolean).join(' ') || undefined;

  const inputEl = (
    <input
      id={id}
      type={resolvedType}
      className={classNames(styles.inputField, inputClassName, {
        [styles.inputError]: error,
        [styles.inputPassword]: isPassword,
      })}
      value={isCheckbox ? undefined : value}
      checked={isCheckbox ? checked : undefined}
      onChange={(e) => {
        if (!onChange) return;
        if (isCheckbox) {
          onChange(e.target.checked);
        } else {
          onChange(e.target.value);
        }
      }}
      onBlur={onBlur}
      onKeyDown={onKeyDown}
      placeholder={placeholder}
      aria-invalid={!!error}
      aria-describedby={describedBy}
      aria-required={required}
      autoComplete={autoComplete}
      required={required}
      minLength={minLength}
      maxLength={maxLength}
      disabled={disabled}
    />
  );

  return (
    <div className={classNames(styles.inputGroup, className)}>
      {label && (
        <label htmlFor={id} className={styles.label}>
          {label} {required && <span className={styles.required} aria-label="required">*</span>}
        </label>
      )}

      {isPassword ? (
        <div className={styles.passwordWrapper}>
          {inputEl}
          <button
            type="button"
            className={styles.passwordToggle}
            onClick={() => setShowPassword(prev => !prev)}
            aria-label={showPassword ? 'Hide password' : 'Show password'}
            disabled={disabled}
          >
            {showPassword ? <EyeOffIcon /> : <EyeIcon />}
          </button>
        </div>
      ) : inputEl}

      {helpText && !error && (
        <p id={helpTextId} className={styles.helpText} role="note">
          {helpText}
        </p>
      )}
      {error && (
        <p id={errorId} className={styles.errorText} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

/* EXAMPLE USAGE

import Input from './Input';

<Input
  id="display-name"
  label="Display Name"
  value={formData.display_name}
  onChange={(val) => setFormData({ ...formData, display_name: val })}
  placeholder="Enter your display name"
  helpText="This will be visible to others"
  error={formData.display_name === '' ? 'Name is required' : ''}
/>
 */
