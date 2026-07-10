import { Injectable } from '@angular/core';
import { HttpEvent, HttpHandler, HttpInterceptor, HttpRequest, HttpErrorResponse } from '@angular/common/http';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  private tokenKey = 'ai_knowledge_token';

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    const token = sessionStorage.getItem(this.tokenKey);

    let authReq = req;
    if (token) {
      authReq = req.clone({
        setHeaders: {
          Authorization: `Bearer ${token}`,
        },
      });
    }

    return next.handle(authReq).pipe(
      tap({
        error: (error) => {
          if (error instanceof HttpErrorResponse && error.status === 401 && !req.url.includes('/auth/login')) {
            // Clear token and reload to reset app state and show login screen
            sessionStorage.removeItem(this.tokenKey);
            window.location.reload();
          }
        }
      })
    );
  }
}





