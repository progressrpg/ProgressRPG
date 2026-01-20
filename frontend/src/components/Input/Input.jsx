import styles from './Input.module.scss';
import classNames from 'classnames';

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
}) {
  const isCheckbox = type === 'checkbox';
  
  const helpTextId = helpText ? `${id}-help` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [helpTextId, errorId].filter(Boolean).join(' ') || undefined;

  return (
    <div className={classNames(styles.inputGroup, className)}>
      {label && (
        <label htmlFor={id} className={styles.label}>
          {label} {required && <span className={styles.required} aria-label="required">*</span>}
        </label>
      )}

      <input
        id={id}
        type={type}
        className={classNames(styles.inputField, inputClassName, {
          [styles.inputError]: error,
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
