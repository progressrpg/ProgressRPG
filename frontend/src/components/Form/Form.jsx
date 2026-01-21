import React, { useState } from 'react';
import styles from './Form.module.scss';
import Button from '../Button/Button';
import ButtonFrame from '../Button/ButtonFrame';
import Input from '../Input/Input';

export default function Form({
  title,
  onSubmit,
  fields = [],
  children,
  submitLabel = 'Submit',
  isSubmitting = false,
  disabled = false,
  className,
  frameClass,
  fieldErrors = {}
}) {
  const [touched, setTouched] = useState({});
  const titleId = 'form-title-' + Math.random().toString(36).substr(2, 9);

   const handleBlur = (name) => {
    setTouched((prev) => ({ ...prev, [name]: true }));
  };

  const getError = (field) => {
    if (fieldErrors[field.name]?.[0]) {
      return fieldErrors[field.name][0];
    }

    if (!touched[field.name]) return '';
    
    if (field.required && !field.value) {
      return 'This field is required';
    }

    if (field.minLength && field.value?.length < field.minLength) {
      return `Must be at least ${field.minLength} characters`;
    }

    if (field.maxLength && field.value?.length > field.maxLength) {
      return `Must be no more than ${field.maxLength} characters`;
    }

    return '';
  };

  return (
    <div className={`${styles.formFrame} ${frameClass || ''}`}>
      {title && <h1 id={titleId} className={styles.formTitle}>{title}</h1>}

      <form 
        onSubmit={onSubmit} 
        className={`${styles.form} ${className || ''}`}
        noValidate
        aria-busy={isSubmitting}
        aria-labelledby={title ? titleId : undefined}
      >

        <div role="group">
          {fields.map(field => (
              <Input
                key={field.name}
                id={field.id || field.name}
                label={field.label || field.name}
                type={field.type}
                value={field.value}
                onChange={field.onChange}
                placeholder={field.placeholder}
                helpText={field.helpText}
                required={field.required}
                autoComplete={field.autoComplete}
                error={getError(field)}
                onBlur={() => handleBlur(field.name)}
                disabled={disabled || isSubmitting}
              />
          ))}
        </div>

        {children}

        <div className={styles.actions}>
          <ButtonFrame>
            <Button
              type="submit"
              className={styles.submitButton}
              disabled={isSubmitting || disabled}
              ariaLabel={isSubmitting ? 'Submitting form' : submitLabel}
            >
              {isSubmitting ? 'Submitting…' : submitLabel}
            </Button>
          </ButtonFrame>
        </div>
      </form>
    </div>
  );
}
