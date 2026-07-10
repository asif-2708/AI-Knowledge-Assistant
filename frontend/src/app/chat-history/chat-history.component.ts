import { Component, ChangeDetectorRef } from '@angular/core';
import { ChatService, ChatMessage } from '../services/chat.service';

@Component({
  selector: 'app-chat-history',
  standalone: false,
  templateUrl: './chat-history.component.html',
  styleUrls: ['./chat-history.component.css'],
})
export class ChatHistoryComponent {
  history: ChatMessage[] = [];

  constructor(
    private chatService: ChatService,
    private cdr: ChangeDetectorRef
  ) {
    this.history = this.chatService.getHistory();
  }

  clear() {
    this.chatService.clearHistory();
    this.history = [];
    this.cdr.detectChanges();
  }
}
