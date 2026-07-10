import { Component, EventEmitter, Output, ChangeDetectorRef } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { AuthService } from '../services/auth.service';

@Component({
  selector: 'app-register',
  standalone: false,
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.css'],
})
export class RegisterComponent {
  @Output() switchToLogin = new EventEmitter<void>();
  
  registerForm = this.fb.group({
    username: ['', Validators.required],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(6)]],
  });

  isLoading = false;
  isSubmitted = false;
  error = '';
  success = '';

  constructor(private fb: FormBuilder, private authService: AuthService, private cdr: ChangeDetectorRef) {}

  get username() {
    return this.registerForm.get('username');
  }

  get email() {
    return this.registerForm.get('email');
  }

  get password() {
    return this.registerForm.get('password');
  }

  onSubmit(): void {
    this.isSubmitted = true;
    if (!this.registerForm.valid) {
      this.registerForm.markAllAsTouched();
      return;
    }
    
    this.isLoading = true;
    this.error = '';
    this.success = '';
    const { username, email, password } = this.registerForm.value;
    
    this.authService.register(username!, email!, password!).subscribe({
      next: () => {
        this.success = 'Registration successful! Redirecting to login...';
        this.isLoading = false;
        this.cdr.detectChanges();
        setTimeout(() => {
          this.switchToLogin.emit();
        }, 1500);
      },
      error: (err) => {
        this.error = err.error?.detail || 'Registration failed';
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }
}
