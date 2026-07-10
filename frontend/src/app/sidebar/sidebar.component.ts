import { Component, EventEmitter, Input, Output } from '@angular/core';
import { AuthService } from '../services/auth.service';

@Component({
  selector: 'app-sidebar',
  standalone: false,
  templateUrl: './sidebar.component.html',
  styleUrls: ['./sidebar.component.css'],
})
export class SidebarComponent {
  @Input() activeTab: string = 'dashboard';
  @Output() tabChange = new EventEmitter<'dashboard' | 'documents' | 'chat-history'>();

  constructor(public auth: AuthService) {}

  selectTab(tab: 'dashboard' | 'documents' | 'chat-history'): void {
    this.tabChange.emit(tab);
  }
}
