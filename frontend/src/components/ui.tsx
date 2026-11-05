import { useId } from 'react';
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from 'react';
import './ui.css';

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' };

export function Button({ variant = 'primary', type = 'button', className = '', ...props }: ButtonProps) {
  return <button type={type} className={`ui-button ui-button--${variant} ${className}`} {...props} />;
}

type TextFieldProps = InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string; hint?: string };

export function TextField({ label, error, hint, id, className = '', 'aria-describedby': describedBy, ...props }: TextFieldProps) {
  const generatedId = useId();
  const fieldId = id ?? generatedId;
  const descriptionId = error || hint ? `${fieldId}-description` : undefined;
  const descriptions = [describedBy, descriptionId].filter(Boolean).join(' ') || undefined;
  return <div className={`ui-field ${className}`}>
    <label htmlFor={fieldId}>{label}</label>
    <input id={fieldId} aria-invalid={error ? true : undefined} aria-describedby={descriptions} {...props} />
    {(error || hint) && <span id={descriptionId} className={error ? 'ui-field__error' : 'ui-field__hint'}>{error || hint}</span>}
  </div>;
}

type NoticeProps = { kind?: 'info' | 'success' | 'warning' | 'error'; children: ReactNode };

export function Notice({ kind = 'info', children }: NoticeProps) {
  return <div className={`ui-notice ui-notice--${kind}`} role={kind === 'error' ? 'alert' : 'status'}>{children}</div>;
}

type PageTemplateProps = { title: string; children: ReactNode; description?: ReactNode };

export function PageTemplate({ title, description, children }: PageTemplateProps) {
  return <main className="ui-page"><h1>{title}</h1>{description && <p>{description}</p>}{children}</main>;
}
