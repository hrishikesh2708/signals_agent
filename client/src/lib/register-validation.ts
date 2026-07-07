/** Client-side register validation — mirrors backend ``UserCreate`` rules. */

export const REGISTER_FIELD_HINTS = {
  email: "Enter a valid email address (e.g. you@example.com)",
  name: "Display name must be 50 characters or fewer",
  password:
    "Use 8+ characters with uppercase, lowercase, a number, and a special character",
} as const;

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PASSWORD_SPECIAL = /[!@#$%^&*(),.?":{}|<>]/;

export function validateRegisterFields(values: {
  email: string;
  name: string;
  password: string;
}): Record<string, string> {
  const errors: Record<string, string> = {};
  const email = values.email.trim();

  if (!email) {
    errors.email = "Email is required";
  } else if (!EMAIL_PATTERN.test(email)) {
    errors.email = REGISTER_FIELD_HINTS.email;
  }

  const name = values.name.trim();
  if (name.length > 50) {
    errors.name = REGISTER_FIELD_HINTS.name;
  }

  const password = values.password;
  if (!password) {
    errors.password = "Password is required"; // pragma: allowlist secret
  } else if (password.length < 8) {
    errors.password = "Password must be at least 8 characters long"; // pragma: allowlist secret
  } else if (!/[A-Z]/.test(password)) {
    errors.password = "Password must contain at least one uppercase letter"; // pragma: allowlist secret
  } else if (!/[a-z]/.test(password)) {
    errors.password = "Password must contain at least one lowercase letter"; // pragma: allowlist secret
  } else if (!/[0-9]/.test(password)) {
    errors.password = "Password must contain at least one number"; // pragma: allowlist secret
  } else if (!PASSWORD_SPECIAL.test(password)) {
    errors.password = "Password must contain at least one special character"; // pragma: allowlist secret
  } else if (password.length > 64) {
    errors.password = "Password must be 64 characters or fewer"; // pragma: allowlist secret
  }

  return errors;
}

export function setRegisterInputValidity(
  input: HTMLInputElement,
  field: keyof typeof REGISTER_FIELD_HINTS,
): void {
  const value = input.value;

  if (field === "email") {
    if (!value.trim()) {
      input.setCustomValidity("Email is required");
      return;
    }
    if (!EMAIL_PATTERN.test(value.trim())) {
      input.setCustomValidity(REGISTER_FIELD_HINTS.email);
      return;
    }
  }

  if (field === "name" && value.trim().length > 50) {
    input.setCustomValidity(REGISTER_FIELD_HINTS.name);
    return;
  }

  if (field === "password") {
    const errors = validateRegisterFields({
      email: "a@b.co",
      name: "",
      password: value,
    });
    if (errors.password) {
      input.setCustomValidity(errors.password);
      return;
    }
  }

  input.setCustomValidity("");
}
