import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { tap, catchError } from 'rxjs/operators';
import { environment } from '../../environments/environment';

export interface UserResponse {
  id: number;
  username: string;
  email: string;
}

interface LoginResponse {
  access_token: string;
  token_type: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private tokenKey = 'ai_knowledge_token';
  private usernameKey = 'ai_knowledge_username';
  public authState$ = new BehaviorSubject<boolean>(this.isAuthenticated());
  public currentUser$ = new BehaviorSubject<UserResponse | null>(null);

  constructor(private http: HttpClient) {
    if (this.isAuthenticated()) {
      this.fetchCurrentUser().subscribe();
    }
  }

  login(username: string, password: string) {
    const form = new FormData();
    form.append('username', username);
    form.append('password', password);
    return this.http.post<LoginResponse>(`${environment.apiUrl}/auth/login`, form).pipe(
      tap((response) => {
        sessionStorage.setItem(this.tokenKey, response.access_token);
        sessionStorage.setItem(this.usernameKey, username);
        this.authState$.next(true);
      }),
      tap(() => {
        this.fetchCurrentUser().subscribe();
      })
    );
  }

  fetchCurrentUser(): Observable<UserResponse | null> {
    return this.http.get<UserResponse>(`${environment.apiUrl}/auth/me`).pipe(
      tap((user) => {
        if (user && user.username) {
          sessionStorage.setItem(this.usernameKey, user.username);
        }
        this.currentUser$.next(user);
      }),
      catchError((err) => {
        console.error('Failed to fetch current user profile:', err);
        this.logout();
        return of(null);
      })
    );
  }

  register(username: string, email: string, password: string) {
    return this.http.post(`${environment.apiUrl}/auth/register`, { username, email, password });
  }

  logout(): void {
    sessionStorage.removeItem(this.tokenKey);
    sessionStorage.removeItem(this.usernameKey);
    this.currentUser$.next(null);
    this.authState$.next(false);
  }

  getToken(): string | null {
    return sessionStorage.getItem(this.tokenKey);
  }

  getUsername(): string | null {
    return sessionStorage.getItem(this.usernameKey);
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }
}
