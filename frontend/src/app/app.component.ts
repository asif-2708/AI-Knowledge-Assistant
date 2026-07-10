import { Component } from '@angular/core';
import { AuthService } from './services/auth.service';

@Component({
  selector: 'app-root',
  standalone: false,
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
})
export class AppComponent {
  activeTab: 'dashboard' | 'documents' | 'chat-history' = 'dashboard';
  authView: 'login' | 'register' = 'login';

  constructor(public authService: AuthService) {}

  setActiveTab(tab: 'dashboard' | 'documents' | 'chat-history'): void {
    this.activeTab = tab;
  }
}
