import { Component, EventEmitter, Output, ChangeDetectorRef } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { AuthService } from '../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: false,
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css'],
})
export class LoginComponent {
  @Output() switchToRegister = new EventEmitter<void>();

  loginForm = this.fb.group({
    username: ['', Validators.required],
    password: ['', Validators.required],
  });

  isLoading = false;
  isSubmitted = false;
  error = '';

  constructor(private fb: FormBuilder, private auth: AuthService, private cdr: ChangeDetectorRef) {}

  get username() {
    return this.loginForm.get('username');
  }

  get password() {
    return this.loginForm.get('password');
  }

  onSubmit(): void {
    this.isSubmitted = true;
    if (!this.loginForm.valid) {
      this.loginForm.markAllAsTouched();
      return;
    }
    this.isLoading = true;
    this.error = '';
    const { username, password } = this.loginForm.value;
    this.auth.login(username!, password!).subscribe({
      next: () => {
        this.isLoading = false;
        this.cdr.detectChanges();
        window.location.reload(); // Force full reload to reset app state and ensure redirect
      },
      error: (err) => {
        this.error = err.error?.detail || 'Login failed. Please check your credentials.';
        this.isLoading = false;
        this.cdr.detectChanges();
      },
    });
  }
}
